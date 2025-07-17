from pydantic import BaseModel


class Complexity(BaseModel):
    # {'before': 5000000, 'query': 39950, 'after': 4960050, 'reset_in_x_seconds': 60}
    before: int
    query: int
    after: int
    reset_in_x_seconds: int
