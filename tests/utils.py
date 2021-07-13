# Don't use this function anywhere else that tests
def quote_ident(a, real_db_connection):
    # quote_ident method implementation for test cases,
    # it's used since original implementation requres a proper connection, and not mock
    return '"{}"'.format(a)
