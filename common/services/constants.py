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

MONDAY_OUTBOUND_DATA_TYPE_MAP = {
    'autonumber': 'numeric',
    'board-relation': 'text',
    'boolean': 'boolean',
    'button': 'text',
    'color': 'text',
    'country': 'text',
    'color-picker': 'text',
    'columns-battery': 'text',
    'date': 'date_time',
    'dependency': 'text',
    'dropdown': 'text_array',
    'duration': 'text',
    'email': 'text',
    'file': 'text_array',
    'formula': 'text',
    'hour': 'text',
    'integration': 'text',
    'link': 'text_with_label',
    'location': 'text',
    'long-text': 'text',
    'lookup': 'text',
    'multiple-person': 'user_emails',
    'name': 'text',
    'numeric': 'numeric',
    'phone': 'numeric',
    'progress': 'text',
    'pulse-id': 'numeric',
    'pulse-log': 'date_time',
    'pulse-updated': 'date_time',
    'rating': 'numeric',
    'subtasks': 'text',
    'tag': 'text_array',
    'text': 'text',
    'timerange': 'text',
    'timezone': 'text',
    'votes': 'numeric',
    'week': 'text',
}
MONDAY_INBOUND_DATA_TYPES_MAP = {
    'autonumber': ['empty_value'],
    'board-relation': ['empty_value'],
    'boolean': ['boolean'],
    'button': ['empty_value'],
    'color': ['empty_value', 'text'],
    'country': ['empty_value'],
    'color-picker': ['empty_value'],
    'columns-battery': ['empty_value'],
    'date': ['empty_value', 'date', 'date_time'],
    'dependency': ['empty_value'],
    'dropdown': ['empty_value', 'text', 'text_array', 'numeric'],
    'duration': ['empty_value'],
    'email': ['empty_value', 'text', 'text_array'],
    'file': ['empty_value'],
    'formula': ['empty_value'],
    'hour': ['empty_value'],
    'integration': ['empty_value'],
    'link': ['empty_value', 'text', 'text_with_label'],
    'location': ['empty_value'],
    'long-text': ['empty_value', 'text', 'text_array', 'numeric', 'date', 'date_time', 'boolean'],
    'lookup': ['empty_value'],
    'multiple-person': ['empty_value', 'user_emails'],
    'name': ['empty_value', 'text', 'text-array', 'numeric'],
    'numeric': ['empty_value', 'numeric'],
    'phone': ['empty_value', 'text', 'numeric'],
    'pulse-id': ['empty_value'],
    'pulse-log': ['empty_value'],
    'pulse-updated': ['empty_value'],
    'rating': ['empty_value', 'numeric'],
    'subtasks': ['empty_value'],
    'tag': ['empty_value', 'text', 'text_array', 'numeric'],
    'text': ['empty_value', 'text', 'text_array', 'numeric', 'date', 'date_time', 'boolean'],
    'timerange': ['empty_value'],
    'timezone': ['empty_value'],
    'votes': ['empty_value'],
    'week': ['empty_value'],
}

USERS_TABLE_COLUMN_DEFINITIONS = [
    {'name': 'id', 'type': 'integer primary key'},
    {'name': 'url', 'type': 'varchar'},
    {'name': 'name', 'type': 'varchar'},
    {'name': 'email', 'type': 'varchar'},
    {'name': 'phone', 'type': 'varchar'},
    {'name': 'teams', 'type': 'array'},
    {'name': 'title', 'type': 'varchar'},
    {'name': 'enabled', 'type': 'boolean'},
    {'name': 'birthday', 'type': 'varchar'},
    {'name': 'is_admin', 'type': 'boolean'},
    {'name': 'is_guest', 'type': 'boolean'},
    {'name': 'location', 'type': 'varchar'},
    {'name': 'join_date', 'type': 'date'},
    {'name': 'created_at', 'type': 'datetime'},
    {'name': 'is_pending', 'type': 'boolean'},
    {'name': 'is_verified', 'type': 'boolean'},
    {'name': 'country_code', 'type': 'varchar'},
    {'name': 'is_view_only', 'type': 'boolean'},
    {'name': 'mobile_phone', 'type': 'varchar'},
    {'name': 'time_zone_identifier', 'type': 'varchar'}
]

TEAMS_TABLE_COLUMN_DEFINITIONS = [
    {'name': 'id', 'type': 'integer primary key'},
    {'name': 'name', 'type': 'varchar'},
    {'name': 'picture_url', 'type': 'varchar'},
    {'name': 'users', 'type': 'array'},
]

BOARD_ACTIVITY_TABLE_COLUMN_DEFINITIONS = [
    {'name': 'id', 'type': 'varchar primary key'},
    {'name': 'event', 'type': 'varchar'},
    {'name': 'user_id', 'type': 'varchar'},
    {'name': 'entity', 'type': 'varchar'},
    {'name': 'account_id', 'type': 'varchar'},
    {'name': 'created_at', 'type': 'varchar'},
    {'name': 'data', 'type': 'variant'}
]

BOOLEAN_OPTIONS = [
    {
        "title": "TRUE",
        "value": "True"
    },
    {
        "title": "FALSE",
        "value": "False"
    }
]

HOUR_OPTIONS = [
    {
        "title": "1",
        "value": 1
    },
    {
        "title": "2",
        "value": 2
    },
    {
        "title": "3",
        "value": 3
    },
    {
        "title": "4",
        "value": 4
    },
    {
        "title": "5",
        "value": 5
    },
    {
        "title": "6",
        "value": 6
    },
    {
        "title": "7",
        "value": 7
    },
    {
        "title": "8",
        "value": 8
    },
    {
        "title": "9",
        "value": 9
    },
    {
        "title": "10",
        "value": 10
    },
    {
        "title": "11",
        "value": 11
    },
    {
        "title": "12",
        "value": 12
    },
    {
        "title": "13",
        "value": 13
    },
    {
        "title": "14",
        "value": 14
    },
    {
        "title": "15",
        "value": 15
    },
    {
        "title": "16",
        "value": 16
    },
    {
        "title": "17",
        "value": 17
    },
    {
        "title": "18",
        "value": 18
    },
    {
        "title": "19",
        "value": 19
    },
    {
        "title": "20",
        "value": 20
    },
    {
        "title": "21",
        "value": 21
    },
    {
        "title": "22",
        "value": 22
    },
    {
        "title": "23",
        "value": 23
    },
    {
        "title": "24",
        "value": 24
    }
]

TIME_OPTIONS = [
    {
        "title": "12AM UTC",
        "value": "00:00:00"
    },
    {
        "title": "1AM UTC",
        "value": "01:00:00"
    },
    {
        "title": "2AM UTC",
        "value": "02:00:00"
    },
    {
        "title": "3AM UTC",
        "value": "03:00:00"
    },
    {
        "title": "4AM UTC",
        "value": "04:00:00"
    },
    {
        "title": "5AM UTC",
        "value": "05:00:00"
    },
    {
        "title": "6AM UTC",
        "value": "06:00:00"
    },
    {
        "title": "7AM UTC",
        "value": "07:00:00"
    },
    {
        "title": "8AM UTC",
        "value": "08:00:00"
    },
    {
        "title": "9AM UTC",
        "value": "09:00:00"
    },
    {
        "title": "10AM UTC",
        "value": "10:00:00"
    },
    {
        "title": "11AM UTC",
        "value": "11:00:00"
    },
    {
        "title": "12PM UTC",
        "value": "12:00:00"
    },
    {
        "title": "1PM UTC",
        "value": "13:00:00"
    },
    {
        "title": "2PM UTC",
        "value": "14:00:00"
    },
    {
        "title": "3PM UTC",
        "value": "15:00:00"
    },
    {
        "title": "4PM UTC",
        "value": "16:00:00"
    },
    {
        "title": "5PM UTC",
        "value": "17:00:00"
    },
    {
        "title": "6PM UTC",
        "value": "18:00:00"
    },
    {
        "title": "7PM UTC",
        "value": "19:00:00"
    },
    {
        "title": "8PM UTC",
        "value": "20:00:00"
    },
    {
        "title": "9PM UTC",
        "value": "21:00:00"
    },
    {
        "title": "10PM UTC",
        "value": "22:00:00"
    },
    {
        "title": "11PM UTC",
        "value": "23:00:00"
    },
]

SNOWFLAKE_OUTBOUND_DATA_TYPE_MAP = {
    'FIXED': 'numeric',
    'REAL': 'numeric',
    'TEXT': 'text',
    'BINARY': 'text',
    'BOOLEAN': 'boolean',
    'DATE': 'date',
    'TIME': 'date_time',
    'TIMESTAMP_LTZ': 'date_time',
    'TIMESTAMP_NTZ': 'date_time',
    'TIMESTAMP_TZ': 'date_time',
    'VARIANT': 'text',
    'OBJECT': 'text',
    'ARRAY': 'text',
    'GEOGRAPHY': 'text'
}
SNOWFLAKE_INBOUND_DATA_TYPES_MAP = {
    'FIXED': ['empty_value', 'numeric'],
    'REAL': ['empty_value', 'numeric'],
    'TEXT': [
        'empty_value',
        'text',
        'text_array',
        'numeric',
        'date',
        'date_time',
        'boolean',
        'user_emails',
        'text_with_label'
    ],
    'BINARY': ['empty_value', 'text'],
    'BOOLEAN': ['empty_value', 'boolean'],
    'DATE': ['empty_value', 'date', 'date_time'],
    'TIME': ['empty_value', 'date_time'],
    'TIMESTAMP_LTZ': ['empty_value', 'date_time'],
    'TIMESTAMP_NTZ': ['empty_value', 'date_time'],
    'TIMESTAMP_TZ': ['empty_value', 'date_time'],
    'VARIANT': ['empty_value', 'text', 'text_array', 'user_emails'],
    'OBJECT': ['empty_value', 'text'],
    'ARRAY': ['empty_value', 'text', 'text_array', 'user_emails'],
    'GEOGRAPHY': ['empty_value', 'text'],
}

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
