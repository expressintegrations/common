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
    'numbers',
    #   'formula', not valid for now
    'long_text',
    'item_id',
    #   'autonumber', not valid for now
    'email',
    'link'
]

UNSUPPORTED_MONDAY_COLUMN_TYPES = [
    'formula',
    'auto_number',
    'progress',
    'button',
]

SNOWFLAKE_RESERVED_KEYWORDS = [
    'ACCOUNT',
    'ALL',
    'ALTER',
    'AND',
    'ANY',
    'AS',
    'BETWEEN',
    'BY',
    'CASE',
    'CAST',
    'CHECK',
    'COLUMN',
    'CONNECT',
    'CONNECTION',
    'CONSTRAINT',
    'CREATE',
    'CROSS',
    'CURRENT',
    'CURRENT_DATE',
    'CURRENT_TIME',
    'CURRENT_TIMESTAMP',
    'CURRENT_USER',
    'DATABASE',
    'DELETE',
    'DISTINCT',
    'DROP',
    'ELSE',
    'EXISTS',
    'FALSE',
    'FOLLOWING',
    'FOR',
    'FROM',
    'FULL',
    'GRANT',
    'GROUP',
    'GSCLUSTER',
    'HAVING',
    'ILIKE',
    'IN',
    'INCREMENT',
    'INNER',
    'INSERT',
    'INTERSECT',
    'INTO',
    'IS',
    'ISSUE',
    'JOIN',
    'LATERAL',
    'LEFT',
    'LIKE',
    'LOCALTIME',
    'LOCALTIMESTAMP',
    'MINUS',
    'NATURAL',
    'NOT',
    'NULL',
    'OF',
    'ON',
    'OR',
    'ORDER',
    'ORGANIZATION',
    'QUALIFY',
    'REGEXP',
    'REVOKE',
    'RIGHT',
    'RLIKE',
    'ROW',
    'ROWS',
    'SAMPLE',
    'SCHEMA',
    'SELECT',
    'SET',
    'SOME',
    'START',
    'TABLE',
    'TABLESAMPLE',
    'THEN',
    'TO',
    'TRIGGER',
    'TRUE',
    'TRY_CAST',
    'UNION',
    'UNIQUE',
    'UPDATE',
    'USING',
    'VALUES',
    'VIEW',
    'WHEN',
    'WHENEVER',
    'WHERE',
    'WITH'
]
