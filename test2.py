
from adapter.config import driver
cypher_query = '''
MATCH (n:DieuLuat)-[r]-(m) WHERE n.id IN ['Luat_HNGD_2014_Dieu_10', 'Luat_HNGD_2014_Dieu_11', 'Luat_HNGD_2014_Dieu_12'] RETURN n.id, type(r), m.id
'''
records, _, _ = driver.execute_query(cypher_query)
for r in records:
    print(r)

