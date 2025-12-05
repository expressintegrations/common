from typing import Dict, List, Optional, Type, TypeVar, Union

from firedantic import AsyncModel, AsyncSubCollection, AsyncSubModel
from firedantic.common import OrderDirection
from firedantic.configurations import CONFIGURATIONS
from firedantic.exceptions import (
    CollectionNotDefined,
    InvalidDocumentID,
    ModelNotFoundError,
)
from google.cloud.firestore import AsyncDocumentReference

TMultiLevelAsyncSubModel = TypeVar(
    "TMultiLevelAsyncSubModel", bound="MultiLevelAsyncSubModel"
)


class MultiLevelAsyncSubCollection(AsyncSubCollection):
    """Collection class that supports multiple levels of nesting.

    Example usage:
    class Alert(MultiLevelAsyncSubModel):
        class Collection(MultiLevelAsyncSubCollection):
            __collection_tpl__ = "apps/{app_id}/accounts/{account_id}/alerts"
    """

    __collection_tpl__: str | None


class MultiLevelAsyncSubModel(AsyncSubModel):
    """Model class that supports multiple levels of nesting with intuitive saving.

    Example usage:

    class Alert(MultiLevelAsyncSubModel):
        class Collection(MultiLevelAsyncSubCollection):
            __collection_tpl__ = "apps/{app_id}/accounts/{account_id}/alerts"

    # Create and save using parent model
    alert = Alert(level="info", message="test")
    await alert.save(parent=account)

    # Or using explicit path args
    alert = Alert(level="info", message="test")
    await alert.save(app_id="app1", account_id="acc1")

    # Find using parent model
    alerts = await Alert.find(parent=account)

    # Or using explicit path args
    alerts = await Alert.find(app_id="app1", account_id="acc1")

    # Get by ID using parent model
    alert = await Alert.get_by_id("alert-123", parent=account)

    # Or using explicit path args
    alert = await Alert.get_by_id("alert-123", app_id="app1", account_id="acc1")
    """

    class Collection(AsyncSubCollection):
        __collection_tpl__: str | None

    @classmethod
    def _get_collection_path(cls, *, parent: AsyncModel | None = None, **kwargs) -> str:
        """Get collection path from template arguments or parent model.

        There are two ways to get the collection path:
        1. Using a parent model (recommended):
           - Parent must be an AsyncModel with get_document_id() method
           - Uses parent's collection path + ID + our collection name
        2. Using template arguments:
           - Uses cls.Collection.__collection_tpl__ with provided kwargs
           - Required when no parent is provided
        """
        if not hasattr(cls, "Collection") or not cls.Collection.__collection_tpl__:
            raise CollectionNotDefined(
                f"Missing collection template for {cls.__name__}"
            )

        # If parent is provided and has a valid collection path, use its path + ID + our collection name
        if (
            parent is not None
            and hasattr(parent, "__collection__")
            and parent.__collection__ is not None
        ):
            parent_path = parent.__collection__
            # Handle both AsyncModel (uses 'id') and AsyncSubModel (uses Collection.__document_id__)
            if isinstance(parent, AsyncModel) and not isinstance(parent, AsyncSubModel):
                parent_id = getattr(parent, "id")
            else:
                parent_id = getattr(parent, parent.Collection.__document_id__)
            if parent_id is None:
                raise ValueError(f"Parent {parent.__class__.__name__} has no ID")
            our_collection = cls.Collection.__collection_tpl__.split("/")[-1]
            return f"{parent_path}/{parent_id}/{our_collection}"

        # Otherwise use template with provided arguments
        format_args = {}
        if parent is not None:
            format_args.update(parent.model_dump(by_alias=True))
        format_args.update(kwargs)

        try:
            return cls.Collection.__collection_tpl__.format(**format_args)
        except KeyError as e:
            missing = str(e).strip("'")
            raise ValueError(f"Missing required path argument: {missing}")

    @classmethod
    def _get_model_for_path(
        cls: Type[TMultiLevelAsyncSubModel], collection_path: str
    ) -> Type[TMultiLevelAsyncSubModel]:
        """Create a model class for a specific collection path."""
        return type(
            cls.__name__,
            (cls,),
            {
                "__collection__": collection_path,
                "__document_id__": cls.Collection.__document_id__,
            },
        )

    async def save(
        self,
        *,
        parent: AsyncModel | None = None,
        exclude_unset: bool = False,
        exclude_none: bool = False,
        merge: bool = True,
        **kwargs,
    ) -> None:
        """Save this model to Firestore.

        If the model already has an ID:
        - Updates the existing document directly
        - No need to provide parent or path arguments

        If creating a new document, specify the location using either:
        1. A parent model (recommended):
           await model.save(parent=parent_model)
        2. Path arguments:
           await model.save(param1="value1", param2="value2")

        Args:
            parent: Parent model that contains this model's collection. Required for
                   new documents. Must have get_document_id() method.
            exclude_unset: Whether to exclude fields that have not been explicitly set
            exclude_none: Whether to exclude fields that have a value of None
            **kwargs: Path arguments for new documents when parent is not provided.
                     Must match the parameters in Collection.__collection_tpl__
        """
        # Get document ID if it exists
        doc_id = getattr(self, self.Collection.__document_id__, None)

        # If we already have a collection path, use it
        if hasattr(self, "__collection__") and self.__collection__ is not None:
            collection_path = self.__collection__
            model_cls = self.__class__
        # Otherwise get collection path and model class from args
        else:
            collection_path = self._get_collection_path(parent=parent, **kwargs)
            model_cls = self._get_model_for_path(collection_path)

        # Get document reference
        if doc_id:
            doc_ref: AsyncDocumentReference = (
                CONFIGURATIONS["db"].collection(collection_path).document(doc_id)
            )
        else:
            doc_ref = CONFIGURATIONS["db"].collection(collection_path).document()

        # Prepare data for save/update
        data = self.model_dump(exclude_unset=exclude_unset, exclude_none=exclude_none)
        if doc_id:
            del data[self.Collection.__document_id__]

        # Save or update
        doc = await doc_ref.get()
        if doc.exists:
            # Update existing document
            data = self.model_dump(exclude_unset=True)
            if doc_id:
                del data[self.Collection.__document_id__]
            await doc_ref.update(data)
        else:
            # Create new document
            await doc_ref.set(data, merge=merge)

        # Update this instance with new ID
        setattr(self, self.Collection.__document_id__, doc_ref.id)

        # Update collection path if we got it from a new model class
        if not hasattr(self, "__collection__") or self.__collection__ is None:
            self.__collection__ = model_cls.__collection__

    @classmethod
    async def find(
        cls: Type[TMultiLevelAsyncSubModel],
        *,
        parent: AsyncModel | None = None,
        filter_: Optional[Dict[str, Union[str, dict]]] = None,
        order_by: Optional[List[tuple[str, OrderDirection]]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **kwargs,
    ) -> List[TMultiLevelAsyncSubModel]:
        """Find models in Firestore.

        There are two ways to specify the collection to search:
        1. Using a parent model (recommended):
           await Model.find(parent=parent_model, filter_={"status": "active"})
        2. Using path arguments:
           await Model.find(param1="value1", param2="value2", filter_={"status": "active"})

        Args:
            parent: Parent model that contains this model's collection. Must have
                   get_document_id() method. Recommended over using path arguments.
            filter_: Optional filter criteria. Dict mapping field names to:
                    - Exact value to match: {"field": "value"}
                    - Dict of operator and value: {"field": {">=": 100}}
            order_by: Optional sorting criteria. List of (field, direction) tuples.
            limit: Optional maximum number of results to return
            offset: Optional number of results to skip
            **kwargs: Path arguments to use when parent is not provided. Must match
                     the parameters in Collection.__collection_tpl__

        Returns:
            List of model instances matching the criteria
        """
        collection_path = cls._get_collection_path(parent=parent, **kwargs)
        model_cls = cls._get_model_for_path(collection_path)

        # Build query
        query = CONFIGURATIONS["db"].collection(collection_path)

        if filter_:
            for key, value in filter_.items():
                if isinstance(value, dict):
                    for op_type, op_value in value.items():
                        query = query.where(key, op_type, op_value)
                else:
                    query = query.where(key, "==", value)

        if order_by:
            for field, direction in order_by:
                query = query.order_by(field, direction=direction)

        if limit is not None:
            query = query.limit(limit)

        if offset is not None:
            query = query.offset(offset)

        # Execute query and create models
        results = []
        async for doc in query.stream():
            if doc.exists:
                data = doc.to_dict()
                if data:
                    data[model_cls.__document_id__] = doc.id
                    results.append(model_cls(**data))

        return results

    @classmethod
    async def find_one(
        cls: Type[TMultiLevelAsyncSubModel],
        *,
        parent: AsyncModel | None = None,
        filter_: Optional[Dict[str, Union[str, dict]]] = None,
        order_by: Optional[List[tuple[str, OrderDirection]]] = None,
        **kwargs,
    ) -> TMultiLevelAsyncSubModel:
        """Find one model in Firestore. Raises ModelNotFoundError if no match is found.

        There are two ways to specify the collection to search:
        1. Using a parent model (recommended):
           await Model.find_one(parent=parent_model, filter_={"status": "active"})
        2. Using path arguments:
           await Model.find_one(param1="value1", param2="value2", filter_={"status": "active"})

        Args:
            parent: Parent model that contains this model's collection. Must have
                   get_document_id() method. Recommended over using path arguments.
            filter_: Optional filter criteria. Dict mapping field names to:
                    - Exact value to match: {"field": "value"}
                    - Dict of operator and value: {"field": {">=": 100}}
            order_by: Optional sorting criteria. List of (field, direction) tuples.
            **kwargs: Path arguments to use when parent is not provided. Must match
                     the parameters in Collection.__collection_tpl__

        Returns:
            Single model instance matching the criteria

        Raises:
            ModelNotFoundError: If no matching model is found
        """
        results = await cls.find(
            parent=parent, filter_=filter_, order_by=order_by, limit=1, **kwargs
        )
        if not results:
            raise ModelNotFoundError(f"No {cls.__name__} found matching criteria")
        return results[0]

    @classmethod
    async def find_with_count(
        cls: Type[TMultiLevelAsyncSubModel],
        *,
        parent: AsyncModel | None = None,
        filter_: Optional[Dict[str, Union[str, dict]]] = None,
        order_by: Optional[List[tuple[str, OrderDirection]]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **kwargs,
    ) -> tuple[List[TMultiLevelAsyncSubModel], int]:
        """Find models in Firestore and get total count for pagination.

        Works the same as find() but also returns the total count of all documents
        that match the filter, ignoring limit and offset. This is useful for
        implementing pagination.

        Args:
            parent: Parent model that contains this model's collection. Must have
                   get_document_id() method. Recommended over using path arguments.
            filter_: Optional filter criteria. Dict mapping field names to:
                    - Exact value to match: {"field": "value"}
                    - Dict of operator and value: {"field": {">=": 100}}
            order_by: Optional sorting criteria. List of (field, direction) tuples.
            limit: Optional maximum number of results to return
            offset: Optional number of results to skip
            **kwargs: Path arguments to use when parent is not provided. Must match
                     the parameters in Collection.__collection_tpl__

        Returns:
            Tuple of (list of model instances matching criteria, total count of all matches)
        """
        collection_path = cls._get_collection_path(parent=parent, **kwargs)
        model_cls = cls._get_model_for_path(collection_path)

        # Build base query with filters
        query = CONFIGURATIONS["db"].collection(collection_path)
        if filter_:
            for key, value in filter_.items():
                if isinstance(value, dict):
                    for op_type, op_value in value.items():
                        query = query.where(key, op_type, op_value)
                else:
                    query = query.where(key, "==", value)

        # Get total count (must be done before applying limit/offset)
        count_agg = await query.count().get()
        total_count = count_agg[0][0].value

        # Apply ordering, limit, offset for results query
        if order_by:
            for field, direction in order_by:
                query = query.order_by(field, direction=direction)

        if limit is not None:
            query = query.limit(limit)

        if offset is not None:
            query = query.offset(offset)

        # Get paginated results
        results = []
        async for doc in query.stream():
            if doc.exists:
                data = doc.to_dict()
                if data:
                    data[model_cls.__document_id__] = doc.id
                    results.append(model_cls(**data))

        return results, total_count

    @classmethod
    async def get_by_doc_id(
        cls: Type[TMultiLevelAsyncSubModel],
        doc_id: str,
        *,
        parent: AsyncModel | None = None,
        **kwargs,
    ) -> TMultiLevelAsyncSubModel:
        """Get a model by document ID from Firestore. Raises ModelNotFoundError if not found.

        There are two ways to specify the collection to search:
        1. Using a parent model (recommended):
           await Model.get_by_doc_id("123", parent=parent_model)
        2. Using path arguments:
           await Model.get_by_doc_id("123", param1="value1", param2="value2")

        Args:
            doc_id: The document ID of the model to get
            parent: Parent model that contains this model's collection. Must have
                   get_document_id() method. Recommended over using path arguments.
            **kwargs: Path arguments to use when parent is not provided. Must match
                     the parameters in Collection.__collection_tpl__

        Returns:
            Model instance with the specified ID

        Raises:
            ModelNotFoundError: If no model exists with the specified ID
        """
        try:
            cls._validate_document_id(doc_id)
        except InvalidDocumentID:
            raise ModelNotFoundError(
                f"No '{cls.__name__}' found with {cls.Collection.__document_id__} '{doc_id}'"
            )

        collection_path = cls._get_collection_path(parent=parent, **kwargs)
        model_cls = cls._get_model_for_path(collection_path)
        document = (
            await CONFIGURATIONS["db"]
            .collection(collection_path)
            .document(doc_id)
            .get()
        )
        if not document.exists:
            raise ModelNotFoundError(
                f"No '{cls.__name__}' found with {model_cls.Collection.__document_id__} '{doc_id}'"
            )

        data = document.to_dict()
        if data is None:
            raise ModelNotFoundError(
                f"No '{cls.__name__}' found with {model_cls.Collection.__document_id__} '{doc_id}'"
            )
        data[model_cls.Collection.__document_id__] = doc_id
        return model_cls(**data)
