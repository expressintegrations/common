BASE_WORKFLOW_ACTION_OBJECTS = [
    {
        "label": "Company",
        "value": "COMPANY"
    },
    {
        "label": "Contact",
        "value": "CONTACT"
    },
    {
        "label": "Deal",
        "value": "DEAL"
    },
    {
        "label": "Invoice",
        "value": "INVOICE"
    },
    {
        "label": "Marketing Event",
        "value": "MARKETING_EVENT"
    },
    {
        "label": "Product",
        "value": "PRODUCT"
    },
    {
        "label": "Ticket",
        "value": "TICKET"
    }
]

BASE_OBJECTS = [
    "0-1",  # contact
    "0-2",  # company
    "0-3",  # deal
    "0-5"  # ticket
]

ALLOWABLE_SNOWFLAKE_PRIMARY_KEY_COLUMNS = [
    'name',
    'color',
    'date',
    'text',
    'numeric',
    #   'formula', not valid for now
    'long-text',
    'pulse-id',
    #   'autonumber', not valid for now
    'email',
    'link'
]

UNSUPPORTED_MONDAY_COLUMN_TYPES = [
    'formula',
    'autonumber',
    'columns-battery',
    'button',
]
