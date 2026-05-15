
from adapter.config import driver
cypher = '''
MATCH (n_goc:DieuLuat) WHERE n_goc.id IN ['Luat_HNGD_2014_Dieu_11']
OPTIONAL MATCH (n_goc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_goc)
// OPTIONAL MATCH (chi_tiet_goc)-[:THAY_THE_BOI*0..]-(chi_tiet_gia_toc)
// WITH n_goc, collect(chi_tiet_goc) + collect(chi_tiet_gia_toc) AS tat_ca_phien_ban
// UNWIND tat_ca_phien_ban AS node_xet_duyet
WITH DISTINCT n_goc, chi_tiet_goc AS chi_tiet_ap_dung
OPTIONAL MATCH (chi_tiet_ap_dung)-[:HUONG_DAN_BOI]->(huong_dan)
OPTIONAL MATCH (huong_dan)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_huong_dan)
RETURN chi_tiet_ap_dung.id, huong_dan.id, chi_tiet_huong_dan.id
'''
records, _, _ = driver.execute_query(cypher)
for r in records: print(r)

