import os
import json
import re
import argparse
from pydantic import BaseModel, Field, model_validator
from typing import Literal, List, Optional, Union
from typing_extensions import Annotated
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import asyncio
from dotenv import load_dotenv

load_dotenv()

# =====================================================================
# 1. CẤU HÌNH & KHỞI TẠO
# =====================================================================
AI_GATEWAY_API_KEY = os.environ.get("VERCEL_AI_GATEWAY_API_KEY")
print(f"API Key: {AI_GATEWAY_API_KEY}")
AI_GATEWAY_BASE_URL = os.environ.get("AI_GATEWAY_BASE_URL", "https://ai-gateway.vercel.sh/v1")

MODEL_NAME = "gpt-5.5"
API_KEY = AI_GATEWAY_API_KEY 
if not API_KEY:
    raise ValueError("Missing API key. Set VERCEL_AI_GATEWAY_API_KEY or OPENAI_API_KEY.")

llm = ChatOpenAI(
    api_key=API_KEY,
    base_url=AI_GATEWAY_BASE_URL,
    model=MODEL_NAME,
    temperature=0,
    max_tokens=4096,
)

LoaiNodeNguNghia = Literal[
    "KhaiNiemPhapLy", "ChuThe", "HanhViPhapLy", "TaiSan", "DieuKien", "QuyenNghiaVu"
]

QuanHeNguNghia = Literal[
    "CAN_CU_THEO", "LA_MOT_LOAI", "CO_QUYEN", "CO_NGHIA_VU", "BI_CAM_LAM", 
    "YEU_CAU_DIEU_KIEN", "BI_CHAN_BOI", "DAN_DEN_HE_QUA", "GIAI_QUYET_BOI", "SO_HUU"
]

# =====================================================================
# 2. SCHEMA PHẲNG (FLAT SCHEMA) KÈM AUTOCLEAN
# =====================================================================

class ThucThe(BaseModel):
    id_thuc_the: str = Field(description="ID duy nhất tạo tự động (VD: node_1, node_2).")
    loai_node: LoaiNodeNguNghia = Field(description="Phân loại node.")
    ten_thuc_the: str = Field(description="Tên chính của thực thể.")
    
    # Gom tất cả properties vào đây dưới dạng Optional
    loai_chu_the: Optional[Literal["Cá nhân", "Tổ chức", "Cơ quan Nhà nước"]] = Field(default=None)
    dinh_nghia: Optional[str] = Field(default=None)
    tinh_trang_hanh_vi: Optional[Literal["Hợp pháp", "Trái pháp luật", "Bị cấm"]] = Field(default=None)
    loai_tai_san: Optional[str] = Field(default=None)
    thoi_diem_tao_lap: Optional[Literal["Trước kết hôn", "Trong thời kỳ hôn nhân", "Sau khi chia tài sản"]] = Field(default=None)
    loai_quyen_nghia_vu: Optional[Literal["Quyền", "Nghĩa vụ", "Cấm"]] = Field(default=None)
    noi_dung_chi_tiet: Optional[str] = Field(default=None)

    @model_validator(mode='after')
    def autoclean_properties(self):
        """
        Bảo vệ dữ liệu: Tự động xóa (set None) các thuộc tính 
        nếu LLM điền nhầm cho loại node không tương ứng.
        """
        if self.loai_node != "ChuThe": 
            self.loai_chu_the = None
        if self.loai_node != "KhaiNiemPhapLy": 
            self.dinh_nghia = None
        if self.loai_node != "HanhViPhapLy": 
            self.tinh_trang_hanh_vi = None
        if self.loai_node != "TaiSan":
            self.loai_tai_san = None
            self.thoi_diem_tao_lap = None
        if self.loai_node != "QuyenNghiaVu": 
            self.loai_quyen_nghia_vu = None
        if self.loai_node not in ["DieuKien", "QuyenNghiaVu"]: 
            self.noi_dung_chi_tiet = None
        return self

class MoiQuanHe(BaseModel):
    source_id: str
    relation: QuanHeNguNghia
    target_id: str

class KetQuaBocTach(BaseModel):
    danh_sach_thuc_the: List[ThucThe]
    danh_sach_quan_he: List[MoiQuanHe]

    @model_validator(mode='after')
    def validate_relationships(self):
        extracted_ids = {entity.id_thuc_the for entity in self.danh_sach_thuc_the}
        for rel in self.danh_sach_quan_he:
            if rel.relation != "CAN_CU_THEO":
                if rel.source_id not in extracted_ids:
                    raise ValueError(f"Lỗi: Source ID '{rel.source_id}' không tồn tại.")
                if rel.target_id not in extracted_ids:
                    raise ValueError(f"Lỗi: Target ID '{rel.target_id}' không tồn tại.")
        return self

# =====================================================================
# 3. HÀM BÓC TÁCH VÀ XUẤT FILE JSON CHO NEO4J
# =====================================================================

async def extract_and_export(text_dieu_luat: str, id_node_cau_truc: str):
    print(f"[*] Đang xử lý bóc tách cho: {id_node_cau_truc}...")
    
    # Rút trích Tên Điều để đặt tên file (VD: Từ 'Luat_HNGD_2014_Dieu_8_Khoan_1...' -> 'Luat_HNGD_2014_Dieu_8')
    match_dieu = re.search(r'(Luat_HNGD_2014_Dieu_\d+)', id_node_cau_truc)
    file_name = f"{match_dieu.group(1)}.json" if match_dieu else "Luat_HNGD_Output.json"

    structured_llm = llm.with_structured_output(KetQuaBocTach)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Bạn là hệ thống trích xuất Đồ thị tri thức Pháp luật.
        QUY TẮC BẮT BUỘC:
        1. Trích xuất Thực thể và Quan hệ theo đúng schema Pydantic. Tuyệt đối không sinh ra các trường có giá trị null.
        2. Nếu văn bản nhắc đến "Nguyên tắc" hoặc "Trách nhiệm", hãy phân loại nó thành node 'QuyenNghiaVu' hoặc 'KhaiNiemPhapLy', KHÔNG được gom vào 'DieuKien'.
        3. MẠNG LƯỚI NGỮ NGHĨA: Mọi thực thể là 'HanhViPhapLy', 'DieuKien', 'QuyenNghiaVu', hoặc 'TaiSan' ĐỀU PHẢI được nối với ít nhất một 'ChuThe' (Ví dụ: [Chủ thể: Nhà nước] -[CO_NGHIA_VU]-> [QuyềnNghĩaVụ: Bảo vệ trẻ em]).
        4. TẤT CẢ các thực thể đều phải có thêm một quan hệ "CAN_CU_THEO" trỏ đích danh về target_id là: {id_node_cau_truc}.
        """),
        ("user", "ID Node: {id_node_cau_truc}\nNội dung cần phân tích: {noi_dung}")
    ])
    
    # 1. Gọi LLM
    result: KetQuaBocTach = await (prompt | structured_llm).ainvoke({
        "id_node_cau_truc": id_node_cau_truc,
        "noi_dung": text_dieu_luat
    })
    
    # 2. Định dạng lại thành JSON chuẩn để import Neo4j
    neo4j_format = {
        "nodes": [],
        "edges": []
    }
    
    for entity in result.danh_sach_thuc_the:
        # Bỏ đi id_thuc_the và loai_node để lấy phần properties còn lại
        props = entity.model_dump(exclude={'id_thuc_the', 'loai_node'})
        neo4j_format["nodes"].append({
            "id": entity.id_thuc_the,
            "label": entity.loai_node,
            "properties": props
        })
        
    for rel in result.danh_sach_quan_he:
        neo4j_format["edges"].append({
            "source": rel.source_id,
            "type": rel.relation,
            "target": rel.target_id  # Sẽ chứa đúng cái Luat_HNGD_2014_Dieu_X_Khoan_Y_Diem_Z
        })
        
    # 3. Ghi ra file
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(neo4j_format, f, ensure_ascii=False, indent=2)
        
    print(f"[+] Hoàn tất! Đã xuất dữ liệu ra file: {file_name}")

# =====================================================================
# 4. CHẠY THEO KHOẢNG ĐIỀU
# =====================================================================
def _extract_dieu_number(file_name: str) -> Optional[int]:
    match = re.search(r"Luat_HNGD_2014_Dieu_(\d+)", file_name)
    return int(match.group(1)) if match else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bóc tách theo khoảng Điều.")
    parser.add_argument("--output-dir", default="output_articles", help="Thư mục chứa file .txt")
    parser.add_argument("--start", type=int, default=None, help="Điều bắt đầu (VD: 8)")
    parser.add_argument("--end", type=int, default=None, help="Điều kết thúc (VD: 20)")
    args = parser.parse_args()

    if args.start is not None and args.end is not None and args.start > args.end:
        raise ValueError("start phải nhỏ hơn hoặc bằng end.")

    output_dir = args.output_dir

    if not os.path.isdir(output_dir):
        raise FileNotFoundError(f"Không tìm thấy thư mục: {output_dir}")

    file_items = []
    for name in os.listdir(output_dir):
        if not name.lower().endswith(".txt"):
            continue

        dieu_number = _extract_dieu_number(name)
        if dieu_number is None:
            print(f"[!] Bỏ qua file không khớp mẫu điều: {name}")
            continue

        if args.start is not None and dieu_number < args.start:
            continue
        if args.end is not None and dieu_number > args.end:
            continue

        file_items.append((dieu_number, os.path.join(output_dir, name), name))

    if not file_items:
        raise FileNotFoundError("Không có file .txt phù hợp với khoảng Điều đã chọn.")

    async def run_all():
        for _, file_path, file_name in sorted(file_items, key=lambda x: x[0]):
            id_node_cau_truc, _ = os.path.splitext(file_name)

            with open(file_path, "r", encoding="utf-8") as f:
                noi_dung = f.read().strip()

            if not noi_dung:
                print(f"[!] Bỏ qua file rỗng: {file_name}")
                continue

            await extract_and_export(text_dieu_luat=noi_dung, id_node_cau_truc=id_node_cau_truc)

    asyncio.run(run_all())