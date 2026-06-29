from __future__ import annotations

import importlib
from dataclasses import dataclass, replace
from typing import Any, Iterable

from server.shared.phrase_match import match_phrase_groups, prepare_question


DIRECT_TOOLS = {"respond", "clarify"}

# Alias legacy khác topic_label
EXTRA_ALIASES: dict[str, tuple[str, ...]] = {
    "cap_duong": ("nghia_vu_cap_duong",),
}

TERM_MAPPING_TRIGGER_SOURCES: dict[str, tuple[str, tuple[str, ...]]] = {
    "cap_duong": (
        "server.infrastructure.neo4j.cypher_templates.cap_duong.term_mapping",
        (
            "quan_he",
            "boi_canh",
            "tinh_trang_nguoi_duoc_cap_duong",
            "khia_canh",
            "khia_canh_muc",
            "ly_do_cham_dut",
            "tinh_trang_thuc_hien",
            "doi_tuong_nhan",
            "doi_tuong_duoc_cap_duong",
        ),
    ),
    "chia_tai_san_sau_ly_hon": (
        "server.infrastructure.neo4j.cypher_templates.chia_tai_san_sau_ly_hon.term_mapping",
        (
            "khia_canh",
            "loai_tai_san",
            "nguon_goc",
            "loai_nghia_vu",
            "nguoi_thu_ba",
            "muc_dich_no",
            "thoi_diem_no",
            "loai_dat",
            "loai_truong_hop",
            "hanh_vi_context",
        ),
    ),
    "che_do_tai_san_cua_vo_chong": (
        "server.infrastructure.neo4j.cypher_templates.tai_san.term_mapping",
        (
            "loai_tai_san",
            "loai_giao_dich",
            "loai_nghia_vu",
        ),
    ),
    "dai_dien_trach_nhiem_vo_chong": (
        "server.infrastructure.neo4j.cypher_templates.dai_dien_trach_nhiem_vo_chong.term_mapping",
        (
            "loai_giao_dich",
            "loai_tai_san",
            "loai_nghia_vu",
            "boi_canh",
            "muc_dich_giao_dich",
        ),
    ),
    "cha_me_con_sau_ly_hon": (
        "server.infrastructure.neo4j.cypher_templates.cha_me_con_sau_ly_hon.term_mapping",
        (
            "khia_canh",
            "doi_tuong_con",
            "nguoi_truc_tiep_nuoi",
            "nguyen_vong_con",
            "hanh_vi_cha_me",
            "thay_doi_nguoi_nuoi",
        ),
    ),
}

BROAD_TERM_MAPPING_PHRASES = frozenset(
    {
        "bán",
        "bệnh",
        "chia",
        "cho",
        "chết",
        "đất",
        "lỗi",
        "nhà",
        "nuôi",
        "sử dụng",
        "tặng",
    }
)

MAX_TERM_MAPPING_PHRASES_PER_RETRIEVER = 80


@dataclass(frozen=True)
class TriggerRule:
    """Rule phrase-based để xác định retriever có liên quan câu hỏi."""

    code: str
    phrase_groups: tuple[tuple[str, ...], ...]
    reason: str

    def matches(self, prepared_question: str) -> bool:
        """Kiểm tra câu hỏi khớp mọi phrase group của rule.

        Args:
            prepared_question: Câu hỏi đã qua prepare_question.

        Returns:
            True nếu rule khớp.
        """
        return match_phrase_groups(self.phrase_groups, prepared_question)


@dataclass(frozen=True)
class RetrieverSpec:
    name: str
    topic_label: str
    domain_group: str
    required_triggers: tuple[TriggerRule, ...]
    support_triggers: tuple[TriggerRule, ...] = ()
    router_description_schema: dict[str, Any] | None = None


def _tr(
    code: str,
    phrase_groups: Iterable[tuple[str, ...]],
    reason: str,
) -> TriggerRule:
    """Tạo TriggerRule từ các phrase group.

    Args:
        code: Mã rule dùng trong audit.
        phrase_groups: Các group phrase (OR trong group, AND giữa group).
        reason: Mô tả lý do rule khớp.

    Returns:
        TriggerRule immutable.
    """
    return TriggerRule(code=code, phrase_groups=tuple(phrase_groups), reason=reason)


# --- Shared phrase groups (export cho benchmark scripts) ---

LY_HON_PHRASES = ("ly hôn", "ly dị", "ly di", "đơn phương", "thuận tình")
TAI_SAN_PHRASES = (
    "tài sản",
    "nhà",
    "đất",
    "sổ đỏ",
    "sổ hồng",
    "quyền sử dụng đất",
    "nợ",
    "vay tiền",
    "khoản vay",
    "vay nợ",
    "chia đôi",
    "chia đều",
    "tiền thưởng", 
    "trúng số", 
    "trúng xổ số", 
    "trúng thưởng xổ số", 
    "tiền trợ cấp", 
    "vật vô chủ", 
    "vật bị chôn giấu", 
    "bị chìm đắm", 
    "vật bị đánh rơi", 
    "bị bỏ quên", 
    "gia súc",
    "gia cầm", 
    "vật nuôi dưới nước", 
    "sở hữu trí tuệ", 
    "công với cách mạng"
)
CHUNG_RIENG_PHRASES = (
    "tài sản chung",
    "tài sản riêng",
    "chung hay riêng",
    "đứng tên",
    "sổ đỏ",
    "sổ hồng",
    "quyền sử dụng đất",
    "khoản nợ",
    "trả nợ",
    "vay tiền",
    "khoản vay",
    "vay nợ",
    "nợ chung",
    "nợ riêng",
    "nghĩa vụ tài sản",
    "thỏa thuận tài sản",
)
XU_PHAT_PHRASES = (
    "xử phạt",
    "mức phạt",
    "bị phạt",
    "phạt tiền",
    "truy cứu",
    "hình sự",
    "tội phạm",
    "tội ngoại tình",
    "chế tài",
    "xử lý",
    "sao không"
)


_RAW_RETRIEVER_SPECS: dict[str, RetrieverSpec] = {
    "quy_dinh_chung_khai_niem_phap_ly": RetrieverSpec(
        name="quy_dinh_chung_khai_niem_phap_ly",
        topic_label="quy_dinh_chung_khai_niem_phap_ly",
        domain_group="general",
        required_triggers=(
            _tr(
                "general_definition",
                (
                    (
                        "khái niệm",
                        "giải thích từ ngữ",
                        "là gì",
                        "được hiểu như thế nào",
                        "phạm vi ba đời",
                        "người thân thích",
                    ),
                ),
                "Cau hoi hoi ve khai niem/giai thich tu ngu phap ly.",
            ),
        ),
    ),
    "dieu_kien_ket_hon": RetrieverSpec(
        name="dieu_kien_ket_hon",
        topic_label="dieu_kien_ket_hon",
        domain_group="ket_hon",
        required_triggers=(
            _tr(
                "marriage_conditions",
                (
                    (
                        "điều kiện kết hôn",
                        "muốn kết hôn",
                        "được kết hôn",
                        "kết hôn có được không",
                        "có được đăng ký kết hôn",
                        "tiền tới hôn nhân",
                        "tuổi kết hôn",
                        "đủ tuổi kết hôn",
                        "cấm kết hôn",
                        "tảo hôn",
                    ),
                ),
                "Cau hoi truc tiep ve dieu kien/cam ket hon.",
            ),
        ),
        support_triggers=(
            _tr(
                "illegal_marriage_age_context",
                (
                    ("kết hôn trái pháp luật", "hủy kết hôn"),
                    ("tuổi", "chưa đủ tuổi", "18 tuổi", "đủ tuổi"),
                ),
                "Can dieu kien ket hon lam boi canh cho ket hon trai phap luat.",
            ),
        ),
    ),
    "dang_ky_ket_hon": RetrieverSpec(
        name="dang_ky_ket_hon",
        topic_label="dang_ky_ket_hon",
        domain_group="ket_hon",
        required_triggers=(
            _tr(
                "marriage_registration",
                (
                    (
                        "đăng ký kết hôn",
                        "giấy đăng ký kết hôn",
                        "thẩm quyền đăng ký",
                        "thủ tục đăng ký",
                        "kết hôn lại",
                        "xác nhận tình trạng hôn nhân",
                        "đăng ký"
                    ),
                ),
                "Cau hoi ve dang ky, tham quyen hoac thu tuc ket hon.",
            ),
        ),
    ),
    "ket_hon_trai_phap_luat": RetrieverSpec(
        name="ket_hon_trai_phap_luat",
        topic_label="ket_hon_trai_phap_luat",
        domain_group="ket_hon",
        required_triggers=(
            _tr(
                "illegal_marriage",
                (
                    (
                        "kết hôn trái pháp luật",
                        "hôn nhân trái pháp luật",
                        "hủy kết hôn",
                        "yêu cầu hủy",
                        "cận huyệt",
                        "chưa đủ tuổi kết hôn",
                        "kết hôn khi chưa đủ",
                        "kết hôn giả",
                        "đã có vợ",
                        "đã có chồng",
                        "một vợ một chồng",
                    ),
                ),
                "Cau hoi ve huy/xu ly ket hon trai phap luat.",
            ),
        ),
        support_triggers=(
            _tr(
                "sanction_illegal_marriage_context",
                (
                    XU_PHAT_PHRASES,
                    ("tảo hôn", "cận huyệt", "một vợ một chồng", "kết hôn trái pháp luật"),
                ),
                "Can quy dinh hanh vi nen truoc khi tra cuu che tai.",
            ),
        ),
    ),
    "chung_song_nhu_vo_chong": RetrieverSpec(
        name="chung_song_nhu_vo_chong",
        topic_label="chung_song_nhu_vo_chong",
        domain_group="ket_hon",
        required_triggers=(
            _tr(
                "cohabitation",
                (
                    (
                        "chung sống như vợ chồng",
                        "sống chung như vợ chồng",
                        "sống thử",
                        "không đăng ký kết hôn",
                        "không có đăng ký kết hôn",
                    ),
                ),
                "Cau hoi ve chung song nhu vo chong khong dang ky ket hon.",
            ),
        ),
        support_triggers=(
            _tr(
                "cohabitation_support",
                (
                    ("không đăng ký kết hôn", "không có đăng ký kết hôn", "sống thử"),
                    ("cấp dưỡng", "con", "tài sản", "chia tay"),
                ),
                "Can boi canh khong dang ky ket hon de xac dinh hau qua ve con/tai san/cap duong.",
            ),
        ),
    ),
    "hon_nhan_cham_dut_do_vo_chong_chet": RetrieverSpec(
        name="hon_nhan_cham_dut_do_vo_chong_chet",
        topic_label="hon_nhan_cham_dut_do_vo_chong_chet",
        domain_group="hon_nhan",
        required_triggers=(
            _tr(
                "death_termination",
                (
                    (
                        "vợ chồng chết",
                        "chồng chết",
                        "vợ chết",
                        "tuyên bố là đã chết",
                        "tuyên bố chết",
                        "chấm dứt hôn nhân do",
                    ),
                ),
                "Cau hoi ve cham dut hon nhan do chet/tuyen bo chet.",
            ),
        ),
    ),
    "quy_dinh_chung_ly_hon": RetrieverSpec(
        name="quy_dinh_chung_ly_hon",
        topic_label="quy_dinh_chung_ly_hon",
        domain_group="ly_hon",
        required_triggers=(
            _tr(
                "general_divorce",
                (
                    LY_HON_PHRASES,
                    (
                        "thủ tục",
                        "đơn phương",
                        "thuận tình",
                        "quyền yêu cầu",
                        "yêu cầu ly hôn",
                        "vợ mới sinh",
                        "mới sinh con",
                        "nộp đơn",
                        "tòa án",
                        "án phí",
                        "thời điểm chấm dứt",
                        "có được ly hôn",
                        "giải quyết ly hôn",
                        "muốn ly hôn", 
                        "không muốn ly hôn",
                        "sắp ly hôn",
                        "sắp ly dị",
                        "chuẩn bị ly hôn",
                        "chuẩn bị ly dị",
                    ),
                ),
                "Cau hoi ve quyen, thu tuc hoac quy dinh chung khi ly hon.",
            ),
        ),
    ),
    "chia_tai_san_sau_ly_hon": RetrieverSpec(
        name="chia_tai_san_sau_ly_hon",
        topic_label="chia_tai_san_sau_ly_hon",
        domain_group="ly_hon",
        required_triggers=(
            _tr(
                "divorce_property",
                (
                    ("ly hôn", "ly dị", "ly di", "sau ly hôn", "khi ly hôn"),
                    TAI_SAN_PHRASES,
                ),
                "Cau hoi co trong tam chia/giai quyet tai san khi ly hon.",
            ),
            _tr(
                "explicit_divorce_property",
                (
                    (
                        "chia tài sản sau ly hôn",
                        "chia tài sản khi ly hôn",
                        "tài sản khi ly hôn",
                        "phân chia tài sản sau",
                    ),
                ),
                "Cau hoi noi truc tiep ve chia tai san sau/khi ly hon.",
            ),
        ),
    ),
    "cha_me_con_sau_ly_hon": RetrieverSpec(
        name="cha_me_con_sau_ly_hon",
        topic_label="cha_me_con_sau_ly_hon",
        domain_group="ly_hon",
        required_triggers=(
            _tr(
                "children_after_divorce",
                (
                    (
                        "nuôi cháu", 
                        "nuôi bé", 
                        "nuôi con",
                        "quyền nuôi con",
                        "giành quyền nuôi",
                        "quyền nuôi cháu",
                        "giành quyền nuôi cháu",
                        "thay đổi người trực tiếp nuôi",
                        "thăm nom",
                        "thăm nuôi",
                        "chăm sóc",
                        "nuôi dưỡng",
                        "trông nom", 
                        "giáo dục", 
                        "sinh con", 
                        "đẻ con", 
                        "nguyện vọng", 
                        "ở với bố", 
                        "ở với mẹ", 
                    ),
                    ("ly hôn", "sau ly hôn", "khi ly hôn", "cha mẹ", "cha đã chết", "cha đã mất", "mẹ đã mất", "mẹ đã chết"),
                ),
                "Cau hoi ve nuoi duong/cham soc/tham nom con sau ly hon.",
            ),
        ),
        support_triggers=(
            _tr(
                "child_support_context",
                (
                    ("cấp dưỡng", "mức cấp dưỡng"),
                    ("ly hôn", "nuôi con"),
                ),
                "Can boi canh cha me con sau ly hon cho cau hoi cap duong nuoi con.",
            ),
        ),
    ),
    "cap_duong": RetrieverSpec(
        name="cap_duong",
        topic_label="cap_duong",
        domain_group="cap_duong",
        required_triggers=(
            _tr(
                "support_obligation",
                (
                    (
                        "cấp dưỡng",
                        "trợ cấp nuôi con",
                        "nghĩa vụ cấp dưỡng",
                        "mức cấp dưỡng",
                        "không cấp dưỡng",
                        "chấm dứt cấp dưỡng",
                    ),
                ),
                "Cau hoi ve nghia vu, muc hoac cham dut cap duong.",
            ),
        ),
    ),
    "che_do_tai_san_cua_vo_chong": RetrieverSpec(
        name="che_do_tai_san_cua_vo_chong",
        topic_label="che_do_tai_san_cua_vo_chong",
        domain_group="tai_san",
        required_triggers=(
            _tr(
                "spousal_property_regime",
                (CHUNG_RIENG_PHRASES,),
                "Cau hoi can xac dinh che do tai san chung/rieng/nghia vu tai san cua vo chong.",
            ),
            _tr(
                "marital_property_period",
                (
                    (
                        "trong thời kỳ hôn nhân",
                        "sau khi kết hôn",
                        "trước khi kết hôn",
                        "độc thân",
                        "mua nhà khi độc thân",
                        "bán phải hỏi ý vợ",
                        "tài sản của vợ chồng",
                        "chế độ tài sản",
                        "thỏa thuận chế độ tài sản",
                        "hợp đồng phân chia tài sản",
                        "phân chia tài sản giữa vợ và chồng",
                        "ly thân",
                    ),
                ),
                "Cau hoi ve che do tai san cua vo chong truoc/trong hon nhan.",
            ),
            _tr(
                "tai_san",
                (TAI_SAN_PHRASES,),
                "Cau hoi de cap cac loai tai san trong che do tai san vo chong.",
            ),
        ),
        support_triggers=(
            _tr(
                "divorce_property_characterization",
                (
                    LY_HON_PHRASES,
                    CHUNG_RIENG_PHRASES + ("tài sản", "chia tài sản"),
                ),
                "Can xac dinh tai san/nghia vu chung-rieng truoc khi chia tai san ly hon.",
            ),
        ),
    ),
    "dai_dien_trach_nhiem_vo_chong": RetrieverSpec(
        name="dai_dien_trach_nhiem_vo_chong",
        topic_label="dai_dien_trach_nhiem_vo_chong",
        domain_group="vo_chong",
        required_triggers=(
            _tr(
                "representation_liability",
                (
                    (
                        "đại diện giữa vợ chồng",
                        "trách nhiệm liên đới",
                        "giao dịch do một bên",
                        "kinh doanh chung",
                        "giấy tờ tài sản chỉ ghi tên",
                        "bán nhà",
                        "thế chấp",
                        "tặng cho",
                        "ai phải đồng ý",
                        "cần đồng ý",
                    ),
                ),
                "Cau hoi ve dai dien/trach nhiem lien doi cua vo chong.",
            ),
        ),
        support_triggers=(
            _tr(
                "debt_liability_support",
                (
                    (
                        "khoản nợ",
                        "trả nợ",
                        "vay tiền",
                        "vay nợ",
                        "khoản vay",
                        "nghĩa vụ tài sản",
                        "trách nhiệm liên đới",
                    ),
                    ("vợ chồng", "ly hôn", "trong thời kỳ hôn nhân"),
                ),
                "Can boi canh trach nhiem lien doi khi xu ly no/nghia vu tai san.",
            ),
        ),
    ),
    "quyen_nghia_vu_vo_chong": RetrieverSpec(
        name="quyen_nghia_vu_vo_chong",
        topic_label="quyen_nghia_vu_vo_chong",
        domain_group="vo_chong",
        required_triggers=(
            _tr(
                "spousal_personal_rights",
                (
                    (
                        "bình đẳng vợ chồng",
                        "tình nghĩa vợ chồng",
                        "nơi cư trú",
                        "danh dự",
                        "nhân phẩm",
                        "uy tín",
                        "tín ngưỡng",
                        "học tập",
                        "làm việc",
                        "ngoại tình",
                    ),
                ),
                "Cau hoi ve quyen/nghia vu nhan than giua vo chong.",
            ),
        ),
    ),
    "quyen_nghia_vu_cha_me_con": RetrieverSpec(
        name="quyen_nghia_vu_cha_me_con",
        topic_label="quyen_nghia_vu_cha_me_con",
        domain_group="cha_me_con",
        required_triggers=(
            _tr(
                "parent_child_rights",
                (
                    (
                        "quyền nghĩa vụ cha mẹ con",
                        "cha mẹ có nghĩa vụ",
                        "con có nghĩa vụ",
                        "chăm sóc giáo dục con",
                        "đại diện cho con",
                        "quản lý tài sản của con",
                    ),
                ),
                "Cau hoi ve quyen/nghia vu chung giua cha me va con.",
            ),
        ),
    ),
    "han_che_quyen_cha_me_con_chua_thanh_nien": RetrieverSpec(
        name="han_che_quyen_cha_me_con_chua_thanh_nien",
        topic_label="han_che_quyen_cha_me_con_chua_thanh_nien",
        domain_group="cha_me_con",
        required_triggers=(
            _tr(
                "parental_right_restriction",
                (
                    (
                        "hạn chế quyền làm cha",
                        "hạn chế quyền làm mẹ",
                        "hạn chế quyền cha mẹ",
                        "ngược đãi con",
                        "phá tan tài sản của con",
                        "xúi giục con",
                        "hạn chế quyền", 
                        "hạn chế"
                    ),
                ),
                "Cau hoi ve han che quyen cua cha me doi voi con chua thanh nien.",
            ),
        ),
    ),
    "xac_dinh_cha_me_con": RetrieverSpec(
        name="xac_dinh_cha_me_con",
        topic_label="xac_dinh_cha_me_con",
        domain_group="cha_me_con",
        required_triggers=(
            _tr(
                "parent_child_identification",
                (
                    (
                        "xác định cha",
                        "xác định mẹ",
                        "xác định con",
                        "nhận cha",
                        "nhận mẹ",
                        "nhận con",
                        "adn",
                        "khai sinh",
                    ),
                ),
                "Cau hoi ve xac dinh quan he cha, me, con.",
            ),
        ),
    ),
    "tai_san_rieng_cua_con": RetrieverSpec(
        name="tai_san_rieng_cua_con",
        topic_label="tai_san_rieng_cua_con",
        domain_group="cha_me_con",
        required_triggers=(
            _tr(
                "child_property",
                (
                    (
                        "tài sản riêng của con",
                        "tài sản của con",
                        "quản lý tài sản con",
                        "định đoạt tài sản của con",
                    ),
                ),
                "Cau hoi ve tai san rieng cua con.",
            ),
        ),
    ),
    "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh": RetrieverSpec(
        name="quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh",
        topic_label="quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh",
        domain_group="family_members",
        required_triggers=(
            _tr(
                "other_family_members",
                (
                    (
                        "ông bà",
                        "anh chị em",
                        "cô dì chú bác",
                        "thành viên khác trong gia đình",
                    ),
                ),
                "Cau hoi ve quyen/nghia vu giua cac thanh vien khac trong gia dinh.",
            ),
        ),
    ),
    "quan_he_hon_nhan_co_yeu_to_nuoc_ngoai": RetrieverSpec(
        name="quan_he_hon_nhan_co_yeu_to_nuoc_ngoai",
        topic_label="quan_he_hon_nhan_co_yeu_to_nuoc_ngoai",
        domain_group="foreign",
        required_triggers=(
            _tr(
                "foreign_element",
                (
                    (
                        "nước ngoài",
                        "người nước ngoài",
                        "quốc tịch",
                        "lãnh sự",
                        "đại sứ quán",
                        "nhật bản",
                        "hàn quốc",
                        "hoa kỳ",
                        "nước mỹ",
                        "nước đức",
                        "cộng hòa pháp",
                    ),
                ),
                "Cau hoi co yeu to nuoc ngoai.",
            ),
        ),
        support_triggers=(
            _tr(
                "foreign_support",
                (
                    (
                        "nước ngoài",
                        "người nước ngoài",
                        "quốc tịch",
                        "lãnh sự",
                        "đại sứ quán",
                        "nhật bản",
                        "hàn quốc",
                        "hoa kỳ",
                        "nước mỹ",
                        "nước đức",
                        "cộng hòa pháp",
                    ),
                    ("kết hôn", "ly hôn", "đăng ký"),
                ),
                "Can boi canh yeu to nuoc ngoai cho ket hon/ly hon/dang ky.",
            ),
        ),
    ),
    "xu_phat_vi_pham": RetrieverSpec(
        name="xu_phat_vi_pham",
        topic_label="xu_phat_vi_pham",
        domain_group="vi_pham",
        required_triggers=(
            _tr(
                "sanction",
                (XU_PHAT_PHRASES,),
                "Cau hoi ve xu phat, che tai, trach nhiem hinh su/hanh chinh.",
            ),
        ),
    ),
}


def _term_mapping_phrase_is_specific(phrase: str) -> bool:
    """Kiểm tra một phrase term_mapping có đủ cụ thể để làm support trigger.

    Args:
        phrase: Cụm từ phổ thông lấy từ COMMON_TO_LEGAL_TERMS.

    Returns:
        True nếu phrase có thể dùng làm trigger bổ sung; False nếu phrase quá ngắn,
        quá rộng hoặc rỗng sau chuẩn hóa.
    """
    prepared_phrase = prepare_question(phrase)
    if not prepared_phrase or prepared_phrase in BROAD_TERM_MAPPING_PHRASES:
        return False
    words = prepared_phrase.split()
    return len(words) >= 2


def _load_term_mapping_phrases(module_path: str, fields: tuple[str, ...]) -> tuple[str, ...]:
    """Nạp phrase đủ cụ thể từ COMMON_TO_LEGAL_TERMS của một module mapping.

    Args:
        module_path: Python import path tới module term_mapping.
        fields: Các field mapping được phép lấy phrase cho retriever tương ứng.

    Returns:
        Tuple phrase không trùng, đã lọc độ cụ thể và giới hạn số lượng; trả tuple
        rỗng nếu module/COMMON_TO_LEGAL_TERMS không tồn tại hoặc field không phù hợp.
    """
    try:
        module = importlib.import_module(module_path)
    except Exception:
        return ()

    mapping = getattr(module, "COMMON_TO_LEGAL_TERMS", None)
    if not isinstance(mapping, dict):
        return ()

    phrases: list[str] = []
    seen: set[str] = set()
    for field in fields:
        field_mapping = mapping.get(field)
        if not isinstance(field_mapping, dict):
            continue
        for raw_phrase in field_mapping:
            phrase = str(raw_phrase or "").strip()
            normalized = prepare_question(phrase)
            if normalized in seen or not _term_mapping_phrase_is_specific(phrase):
                continue
            seen.add(normalized)
            phrases.append(phrase)

    phrases.sort(key=lambda item: (-len(prepare_question(item).split()), prepare_question(item)))
    return tuple(phrases[:MAX_TERM_MAPPING_PHRASES_PER_RETRIEVER])


def _enrich_specs_with_term_mapping_triggers(
    specs: dict[str, RetrieverSpec],
) -> dict[str, RetrieverSpec]:
    """Bổ sung support trigger từ term_mapping cho các retriever được whitelist.

    Args:
        specs: Dict RetrieverSpec đã có router_description_schema nếu có.

    Returns:
        Dict RetrieverSpec mới, trong đó một số retriever có thêm support trigger
        term_mapping; retriever không có source hoặc không có phrase hợp lệ giữ nguyên.
    """
    enriched: dict[str, RetrieverSpec] = dict(specs)
    for spec_name, (module_path, fields) in TERM_MAPPING_TRIGGER_SOURCES.items():
        spec = enriched.get(spec_name)
        if spec is None:
            continue
        phrases = _load_term_mapping_phrases(module_path, fields)
        if not phrases:
            continue
        trigger = _tr(
            "term_mapping_support",
            (phrases,),
            "Matched curated term_mapping phrase for retriever.",
        )
        enriched[spec_name] = replace(
            spec,
            support_triggers=spec.support_triggers + (trigger,),
        )
    return enriched


def _enrich_primary_specs() -> dict[str, RetrieverSpec]:
    """Gắn router schema và support trigger bổ sung vào spec gốc.

    Returns:
        Dict keyed by tên retriever chính, đã enrich description và term_mapping.
    """
    from server.agents.retrievers._descriptions import enrich_specs_with_adapter_descriptions

    specs = enrich_specs_with_adapter_descriptions(_RAW_RETRIEVER_SPECS)
    return _enrich_specs_with_term_mapping_triggers(specs)


def _build_spec_index(primary_specs: dict[str, RetrieverSpec]) -> dict[str, RetrieverSpec]:
    """Tạo index tra cứu theo tên retriever và alias legacy.

    Args:
        primary_specs: Spec gốc keyed by spec.name.

    Returns:
        Index nhiều key trỏ cùng RetrieverSpec, không đổi tên đầu vào.
    """
    index: dict[str, RetrieverSpec] = {}
    for spec in primary_specs.values():
        index[spec.name] = spec
    for spec_name, aliases in EXTRA_ALIASES.items():
        spec = primary_specs.get(spec_name)
        if spec:
            for alias in aliases:
                index[alias] = spec
    return index


PRIMARY_RETRIEVER_SPECS: dict[str, RetrieverSpec] = _enrich_primary_specs()
RETRIEVER_SPECS: dict[str, RetrieverSpec] = _build_spec_index(PRIMARY_RETRIEVER_SPECS)


def retriever_topic_key(tool_name: str) -> str:
    """Khóa so sánh metric: topic_label nếu biết spec, ngược lại tên gốc.

    Args:
        tool_name: Tên tool từ router hoặc benchmark.

    Returns:
        topic_label hoặc tool_name nếu không tra được spec.
    """
    spec = get_retriever_spec(tool_name)
    if spec is not None:
        return spec.topic_label
    return tool_name


def get_retriever_spec(tool_name: str) -> RetrieverSpec | None:
    """Tra cứu RetrieverSpec theo tên gốc từ router (không đổi tên).

    Args:
        tool_name: Tên tool router trả về.

    Returns:
        RetrieverSpec nếu biết, None nếu không có trong index hoặc là direct tool.
    """
    if tool_name in DIRECT_TOOLS:
        return None
    return RETRIEVER_SPECS.get(tool_name)


def unique_retriever_specs() -> list[RetrieverSpec]:
    """Danh sách spec duy nhất theo spec.name (cho router tool registry).

    Returns:
        List RetrieverSpec không trùng.
    """
    seen: set[str] = set()
    out: list[RetrieverSpec] = []
    for spec in PRIMARY_RETRIEVER_SPECS.values():
        if spec.name in seen:
            continue
        seen.add(spec.name)
        out.append(spec)
    return out


def specs_by_topic() -> dict[str, RetrieverSpec]:
    """Map topic_label -> spec (mỗi topic một spec).

    Returns:
        Dict topic_label tới RetrieverSpec.
    """
    return {spec.topic_label: spec for spec in PRIMARY_RETRIEVER_SPECS.values()}


# Alias tương thích benchmark scripts cũ gọi normalize_question
normalize_question = prepare_question
