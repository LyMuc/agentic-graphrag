
from adapter.config import driver
cypher = '''
MATCH (n:DieuLuat) WHERE n.id = 'ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_2'
RETURN n.id, n.ngay_co_hieu_luc, n.ngay_het_hieu_luc
'''
records, _, _ = driver.execute_query(cypher)
for r in records: print(r)

