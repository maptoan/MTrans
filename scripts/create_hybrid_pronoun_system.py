#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tạo hệ thống đại từ nhân xưng lai kết hợp ưu điểm của cả hai hệ thống
"""

import csv
import os
import sys
from collections import defaultdict

# Thêm src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.logger import setup_main_logger

logger = setup_main_logger("HybridPronounSystem")

class HybridPronounSystemCreator:
    """Tạo hệ thống đại từ nhân xưng lai"""
    
    def __init__(self):
        """Khởi tạo creator"""
        self.proposed_rules = []
        self.current_data = []
        self.hybrid_system = []
        
    def load_data(self):
        """Load dữ liệu từ cả hai hệ thống"""
        # Load dữ liệu hiện tại
        try:
            with open("data/metadata/pronoun_metadata.csv", 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.current_data = list(reader)
            logger.info(f"Đã load {len(self.current_data)} dòng dữ liệu hiện tại")
        except Exception as e:
            logger.error(f"Lỗi load dữ liệu hiện tại: {e}")
        
        # Load quy tắc đề xuất
        proposed_data = """Nhóm Giới Tính,Đối Tượng Được Nhắc Tới,Ngôi/Số,Mối Quan Hệ (Người nói -> Người được nhắc tới),Cách Gọi (Đại từ/Danh xưng),Ví Dụ Cụ Thể
NAM,Nam chính (Main Character),Số ít,Tác Giả Tường Thuật,Hắn+Chàng+Gã+Tiểu tử+Thiếu niên,
NAM,Nam chính (Main Character),Số ít,Sư phụ / Trưởng bối (gọi Nam chính),Hắn+Tiểu tử+Nghịch đồ+(Tên riêng),
NAM,Nam chính (Main Character),Số ít,Sư huynh / Sư tỷ (gọi Nam chính),Hắn+Sư đệ+(Tên riêng),
NAM,Nam chính (Main Character),Số ít,Sư đệ / Sư muội (gọi Nam chính),Hắn+Sư huynh+Ca ca,"Lâm sư huynh"
NAM,Nam chính (Main Character),Số ít,Đệ tử (gọi Nam chính),Sư phụ+Sư tôn+Lão sư+Ngài,
NAM,Nam chính (Main Character),Số ít,Hậu cung (vợ/người yêu),Chàng+Phu quân+Hắn+Tên đáng ghét (lúc giận dỗi),
NAM,Nam chính (Main Character),Số ít,Huynh đệ / Bạn bè,Hắn+Tên kia+Đại ca+Lão đệ,"Lâm huynh"
NAM,Nam chính (Main Character),Số ít,Cha / Mẹ (Trưởng bối trong gia tộc),Nó+Hắn+Con ta+Nghịch tử,
NAM,Nam chính (Main Character),Số ít,Bề tôi / Cấp dưới (Hoàng triều / Tông môn),Đại nhân+Chủ nhân+Thiếu chủ+Công tử+Ngài,
NAM,Nam chính (Main Character),Số ít,Người ngoài / Ngang hàng (Trung lập),Hắn+Y+Vị đạo hữu này,"Lâm công tử"
NAM,Nam chính (Main Character),Số ít,Kẻ thù / Đối thủ,Tiểu tử+Thằng nhãi+Tên kia+Gã+Hắn,"Họ Lâm kia"
NAM,Nam quyền quý/cấp cao,Số ít,Tác Giả Tường Thuật,Y+Hắn+Lão+(Chức danh),
NAM,Nam quyền quý/cấp cao,Số ít,Vua -> Bề tôi / Đệ tử (Kính trọng),Bệ hạ+Hoàng thượng+Ngài,
NAM,Nam quyền quý/cấp cao,Số ít,Sư tôn / Lão tổ -> Đệ tử (Kính trọng),Sư tôn+Lão tổ+Tiền bối+Ngài,
NAM,Nam quyền quý/cấp cao,Số ít,Ngang hàng (Vua khác / Lão tổ khác),Hắn+Y+Bệ hạ+Lão quái vật,
NAM,Nam quyền quý/cấp cao,Số ít,Cấp dưới / Người dân (Nói lén / Thù địch),Hắn+Y+Lão tặc+Hôn quân+Lão già,
NAM,Nam phản diện / Tà tu,Số ít,Tác Giả Tường Thuật,Hắn+Gã+Y+Lão (nếu già),
NAM,Nam phản diện / Tà tu,Số ít,Người thường / Chính phái (Sợ hãi / Căm ghét),Tên ma đầu+Gã+Hắn+Lão quỷ+Y,
NAM,Nam phản diện / Tà tu,Số ít,Đồng bọn / Cấp dưới,Đại ca+Chủ nhân+Ma quân+Ngài,
NỮ,Nữ chính / Hậu cung,Số ít,Tác Giả Tường Thuật,Nàng+Cô / Cô gái / Thiếu nữ+Ả / Thị (hiếm),
NỮ,Nữ chính / Hậu cung,Số ít,Nam chính (gọi Nữ chính / Hậu cung),Nàng+Nha đầu+Bảo bối+Tiểu yêu tinh+(Tên riêng),
NỮ,Nữ chính / Hậu cung,Số ít,Sư phụ / Trưởng bối (gọi Nữ chính),Nó+Nha đầu+Cô gái+(Tên riêng),
NỮ,Nữ chính / Hậu cung,Số ít,Sư huynh / Sư đệ (gọi Nữ chính),Nàng+Cô+Sư tỷ / Sư muội,"Lý sư muội"
NỮ,Nữ chính / Hậu cung,Số ít,Tỷ muội (trong hậu cung / tông môn),Nàng+Muội muội+Tỷ tỷ,"Tiểu muội"
NỮ,Nữ chính / Hậu cung,Số ít,Cha / Mẹ (Trưởng bối),Nó+Con gái+Nha đầu,
NỮ,Nữ chính / Hậu cung,Số ít,Người ngoài (Ngưỡng mộ / Trung lập),Nàng+Cô+Tiên tử+Cô nương,"Lý tiên tử"
NỮ,Nữ chính / Hậu cung,Số ít,Tình địch / Kẻ thù,Ả+Con nhỏ đó+Nó+Tiện nhân+Yêu tinh,
NỮ,Nữ quyền quý/cấp cao,Số ít,Tác Giả Tường Thuật,Bà+Y+Thị+Nàng (nếu trẻ đẹp)+(Chức danh),
NỮ,Nữ quyền quý/cấp cao,Số ít,Nữ đế / Hoàng hậu -> Bề tôi (Kính trọng),Bệ hạ (Nữ đế)+Nương nương+Ngài,
NỮ,Nữ quyền quý/cấp cao,Số ít,Sư thái / Trưởng lão (Nữ) -> Đệ tử (Kính trọng),Sư thái+Lão bà bà+Tiền bối+Bà,
NỮ,Nữ quyền quý/cấp cao,Số ít,Ngang hàng (Vua / Lão tổ khác),Bà+Y+Nàng,
NỮ,Nữ quyền quý/cấp cao,Số ít,Cấp dưới / Người dân (Nói lén / Thù địch),Mụ già+Lão yêu bà+Ả+Bà ta,
NỮ,Nữ phản diện / Ma nữ,Số ít,Tác Giả Tường Thuật,Ả+Thị+Mụ (nếu già)+Nàng (nếu đẹp),
NỮ,Nữ phản diện / Ma nữ,Số ít,Người thường / Chính phái (Căm ghét / Khinh miệt),Yêu nữ+Ma nữ+Ả+Con mụ+Ả ta,
NỮ,Nữ phản diện / Ma nữ,Số ít,Cấp dưới / Đồng bọn,Chủ nhân+Đại tỷ+Ma hậu+Ngài,
TRUNG TÍNH/PHI NHÂN,Yêu thú / Linh thú,Số ít,Tác Giả Tường Thuật,Nó+Con thú+Hắn / Nàng / Y (linh trí cao),
TRUNG TÍNH/PHI NHÂN,Yêu thú / Linh thú,Số ít,Chủ nhân (gọi Linh thú),Nó+Bé con+(Tên riêng),
TRUNG TÍNH/PHI NHÂN,Yêu thú / Linh thú,Số ít,Người ngoài (Kẻ thù),Súc sinh+Con quái+Nghiệt súc+Nó,
TRUNG TÍNH/PHI NHÂN,Yêu thú / Linh thú,Số ít,Người ngoài (Kính trọng Yêu vương),Đại nhân+Yêu vương+Ngài,
TRUNG TÍNH/PHI NHÂN,Ma tộc / Chủng tộc khác,Số ít,Tác Giả Tường Thuật,Hắn / Gã (Nam)+Ả / Thị (Nữ)+Nó+Y (cấp cao),
TRUNG TÍNH/PHI NHÂN,Ma tộc / Chủng tộc khác,Số ít,Nhân tộc (Khinh miệt / Thù địch),Tên ma đầu+Lũ ma tộc+Nó+Gã,
TRUNG TÍNH/PHI NHÂN,Ma tộc / Chủng tộc khác,Số ít,Ma tộc (Tôn sùng cấp trên),Ma vương+Chủ nhân+Ngài,
TRUNG TÍNH/PHI NHÂN,Vật phẩm / Pháp bảo,Số ít,Tác Giả Tường Thuật,Nó+Vật ấy+Thứ đó+(Tên vật phẩm),
TRUNG TÍNH/PHI NHÂN,Vật phẩm / Pháp bảo,Số ít,Chủ nhân,Nó+Bảo bối+(Tên vật phẩm),
TRUNG TÍNH/PHI NHÂN,Vật phẩm / Pháp bảo,Số ít,Người ngoài,Thứ đó+Món bảo vật+Nó,
SỐ NHIỀU (CHUNG),Nhóm người (chung),Số nhiều,Tác Giả Tường Thuật,Bọn họ / Họ+Chúng (tiêu cực)+Đám người,
SỐ NHIỀU (CHUNG),Nhóm người (chung),Số nhiều,Nhân vật khác (Trung lập),Bọn họ+Những người đó+Họ,
SỐ NHIỀU (CHUNG),Nhóm người (chung),Số nhiều,Nhân vật khác (Kính trọng - Hội nghị / Tông môn),Chư vị+Các vị+Các vị tiền bối+Các đạo hữu,
SỐ NHIỀU (CHUNG),Nhóm người (chung),Số nhiều,Nhân vật khác (Khinh miệt / Thù địch),Bọn+Lũ+Đám,"Lũ tép riu"+ "Bọn phế vật"
SỐ NHIỀU (NAM),Nhóm người nam (Huynh đệ / Binh lính),Số nhiều,Tác Giả Tường Thuật,Bọn họ / Họ+Chúng (tiêu cực)+Đám nam nhân,
SỐ NHIỀU (NAM),Nhóm người nam (Huynh đệ / Binh lính),Số nhiều,Nhân vật khác (Thân mật - Nam gọi),Huynh đệ chúng ta+Các huynh đệ,
SỐ NHIỀU (NAM),Nhóm người nam (Huynh đệ / Binh lính),Số nhiều,Nhân vật khác (Khinh miệt),Bọn đàn ông+Lũ nam nhân+Đám tiểu tử,
SỐ NHIỀU (NỮ),Nhóm người nữ (Hậu cung / Nữ đệ tử),Số nhiều,Tác Giả Tường Thuật,Bọn họ / Họ+Các nàng / Chư nữ (Hậu cung)+Đám nữ nhân,
SỐ NHIỀU (NỮ),Nhóm người nữ (Hậu cung / Nữ đệ tử),Số nhiều,Nhân vật khác (Thân mật - Nữ gọi),Tỷ muội chúng ta+Các tỷ muội,
SỐ NHIỀU (NỮ),Nhóm người nữ (Hậu cung / Nữ đệ tử),Số nhiều,Nhân vật khác (Khinh miệt / Ghen tuông),Bọn đàn bà+Lũ tiện nhân+Đám hồ ly tinh,
SỐ NHIỀU (PHI NHÂN),Nhóm Yêu / Ma,Số nhiều,Tác Giả Tường Thuật,Chúng+Bầy / Lũ / Đàn,
SỐ NHIỀU (PHI NHÂN),Nhóm Yêu / Ma,Số nhiều,Nhân tộc (Thù địch),Lũ yêu ma+Bọn súc sinh+Chúng,
SỐ NHIỀU (PHI NHÂN),Nhóm Yêu / Ma,Số nhiều,Trong tộc (gọi lẫn nhau),Đồng bào+Tộc nhân+Chúng ta,"""
        
        lines = proposed_data.strip().split('\n')
        reader = csv.DictReader(lines)
        self.proposed_rules = list(reader)
        logger.info(f"Đã load {len(self.proposed_rules)} quy tắc đề xuất")
    
    def create_hybrid_system(self):
        """Tạo hệ thống lai"""
        logger.info("Bắt đầu tạo hệ thống lai...")
        
        # Tạo mapping từ dữ liệu hiện tại
        current_mapping = defaultdict(list)
        for record in self.current_data:
            char = record.get('Character_Name', '')
            pronoun = record.get('Suggested_VN_Pronoun', '')
            context = record.get('Pronoun_Context', '')
            relationship = record.get('Speaker_Relationship', '')
            formality = record.get('Formality_Level', '')
            emotion = record.get('Emotional_Tone', '')
            scene = record.get('Scene_Type', '')
            frequency = record.get('Frequency', '')
            
            if char and pronoun:
                key = f"{char}_{context}_{relationship}_{formality}_{emotion}_{scene}"
                current_mapping[key].append({
                    'pronoun': pronoun,
                    'frequency': frequency,
                    'context': context,
                    'relationship': relationship,
                    'formality': formality,
                    'emotion': emotion,
                    'scene': scene
                })
        
        # Tạo hệ thống lai từ quy tắc đề xuất
        for rule in self.proposed_rules:
            gender_group = rule.get('Nhóm Giới Tính', '')
            object_type = rule.get('Đối Tượng Được Nhắc Tới', '')
            grammatical_person = rule.get('Ngôi/Số', '')
            relationship = rule.get('Mối Quan Hệ (Người nói -> Người được nhắc tới)', '')
            pronoun_forms = rule.get('Cách Gọi (Đại từ/Danh xưng)', '')
            example = rule.get('Ví Dụ Cụ Thể', '')
            
            if not pronoun_forms:
                continue
            
            # Parse pronoun forms
            pronouns = [p.strip() for p in pronoun_forms.split('+') if p.strip()]
            
            # Tạo các quy tắc cho từng ngữ cảnh
            contexts = ['narration', 'dialogue', 'internal_monologue']
            formality_levels = ['formal', 'semi-formal', 'informal', 'intimate']
            emotional_tones = ['neutral', 'respectful', 'affectionate', 'contemptuous', 'angry', 'playful']
            scene_types = ['general', 'combat', 'romantic', 'action', 'dialogue']
            
            for context in contexts:
                for formality in formality_levels:
                    for emotion in emotional_tones:
                        for scene in scene_types:
                            # Xác định đại từ phù hợp dựa trên ngữ cảnh
                            selected_pronouns = self._select_pronouns_for_context(
                                pronouns, context, formality, emotion, scene
                            )
                            
                            if selected_pronouns:
                                # Tạo quy tắc lai
                                hybrid_rule = {
                                    'Gender_Group': gender_group,
                                    'Object_Type': object_type,
                                    'Grammatical_Person': grammatical_person,
                                    'Relationship': relationship,
                                    'Context': context,
                                    'Formality_Level': formality,
                                    'Emotional_Tone': emotion,
                                    'Scene_Type': scene,
                                    'Suggested_Pronouns': '|'.join(selected_pronouns),
                                    'All_Pronouns': '|'.join(pronouns),
                                    'Example': example,
                                    'Priority': self._calculate_priority(context, formality, emotion, scene),
                                    'Usage_Rule': self._generate_usage_rule(relationship, context, formality, emotion),
                                    'Frequency': self._get_frequency_from_current_data(
                                        gender_group, object_type, relationship, context, formality, emotion
                                    )
                                }
                                
                                self.hybrid_system.append(hybrid_rule)
        
        logger.info(f"Đã tạo {len(self.hybrid_system)} quy tắc lai")
    
    def _select_pronouns_for_context(self, pronouns, context, formality, emotion, scene):
        """Chọn đại từ phù hợp cho ngữ cảnh"""
        selected = []
        
        # Mapping cơ bản
        context_mapping = {
            'narration': ['hắn', 'nàng', 'anh', 'cô', 'chàng', 'nàng', 'ông', 'bà'],
            'dialogue': ['anh', 'cô', 'cậu', 'nàng', 'chàng', 'nàng', 'ông', 'bà'],
            'internal_monologue': ['hắn', 'nàng', 'anh', 'cô', 'cậu', 'nàng']
        }
        
        formality_mapping = {
            'formal': ['anh', 'cô', 'ông', 'bà', 'ngài'],
            'semi-formal': ['anh', 'cô', 'cậu', 'nàng'],
            'informal': ['hắn', 'nàng', 'cậu', 'nàng'],
            'intimate': ['chàng', 'nàng', 'anh', 'em']
        }
        
        emotion_mapping = {
            'respectful': ['anh', 'cô', 'ông', 'bà', 'ngài'],
            'affectionate': ['chàng', 'nàng', 'anh', 'em'],
            'contemptuous': ['hắn', 'gã', 'ả', 'nó'],
            'angry': ['hắn', 'gã', 'ả', 'nó'],
            'playful': ['cậu', 'nàng', 'anh', 'em'],
            'neutral': ['anh', 'cô', 'hắn', 'nàng']
        }
        
        # Lọc đại từ dựa trên ngữ cảnh
        context_pronouns = context_mapping.get(context, pronouns)
        formality_pronouns = formality_mapping.get(formality, pronouns)
        emotion_pronouns = emotion_mapping.get(emotion, pronouns)
        
        # Tìm giao điểm
        for pronoun in pronouns:
            if (pronoun in context_pronouns and 
                pronoun in formality_pronouns and 
                pronoun in emotion_pronouns):
                selected.append(pronoun)
        
        # Nếu không có giao điểm, lấy đại từ phù hợp nhất
        if not selected:
            if context == 'narration':
                selected = [p for p in pronouns if p in ['hắn', 'nàng', 'anh', 'cô']]
            elif context == 'dialogue':
                selected = [p for p in pronouns if p in ['anh', 'cô', 'cậu', 'nàng']]
            else:
                selected = pronouns[:2]  # Lấy 2 đại từ đầu
        
        return selected[:3]  # Tối đa 3 đại từ
    
    def _calculate_priority(self, context, formality, emotion, scene):
        """Tính độ ưu tiên của quy tắc"""
        priority = 0
        
        # Ngữ cảnh
        if context == 'narration':
            priority += 3
        elif context == 'dialogue':
            priority += 2
        else:
            priority += 1
        
        # Cấp độ trang trọng
        if formality == 'formal':
            priority += 3
        elif formality == 'semi-formal':
            priority += 2
        else:
            priority += 1
        
        # Cảm xúc
        if emotion == 'neutral':
            priority += 3
        elif emotion in ['respectful', 'affectionate']:
            priority += 2
        else:
            priority += 1
        
        return priority
    
    def _generate_usage_rule(self, relationship, context, formality, emotion):
        """Tạo quy tắc sử dụng"""
        rules = []
        
        if context == 'narration':
            rules.append("Sử dụng trong tường thuật")
        elif context == 'dialogue':
            rules.append("Sử dụng trong hội thoại")
        
        if formality == 'formal':
            rules.append("Trang trọng")
        elif formality == 'informal':
            rules.append("Thân mật")
        
        if emotion == 'respectful':
            rules.append("Tôn trọng")
        elif emotion == 'contemptuous':
            rules.append("Khinh miệt")
        
        return "; ".join(rules)
    
    def _get_frequency_from_current_data(self, gender_group, object_type, relationship, context, formality, emotion):
        """Lấy tần suất từ dữ liệu hiện tại"""
        # Tìm kiếm trong dữ liệu hiện tại
        for record in self.current_data:
            if (record.get('Pronoun_Context') == context and
                record.get('Formality_Level') == formality and
                record.get('Emotional_Tone') == emotion):
                return record.get('Frequency', 'Medium')
        
        return 'Medium'
    
    def save_hybrid_system(self, output_file: str = "data/metadata/hybrid_pronoun_system.csv"):
        """Lưu hệ thống lai"""
        if not self.hybrid_system:
            logger.warning("Không có dữ liệu để lưu")
            return
        
        # Sắp xếp theo độ ưu tiên
        self.hybrid_system.sort(key=lambda x: x['Priority'], reverse=True)
        
        # Lưu file CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'Gender_Group', 'Object_Type', 'Grammatical_Person', 'Relationship',
                'Context', 'Formality_Level', 'Emotional_Tone', 'Scene_Type',
                'Suggested_Pronouns', 'All_Pronouns', 'Example', 'Priority',
                'Usage_Rule', 'Frequency'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.hybrid_system)
        
        logger.info(f"Đã lưu hệ thống lai vào {output_file}")
        return output_file
    
    def generate_summary_report(self):
        """Tạo báo cáo tóm tắt"""
        report = []
        
        report.append("# BÁO CÁO HỆ THỐNG ĐẠI TỪ NHÂN XƯNG LAI")
        report.append("=" * 50)
        report.append("")
        
        report.append("## Tổng quan:")
        report.append(f"- **Tổng số quy tắc:** {len(self.hybrid_system):,}")
        report.append(f"- **Số nhóm giới tính:** {len(set(r['Gender_Group'] for r in self.hybrid_system))}")
        report.append(f"- **Số loại đối tượng:** {len(set(r['Object_Type'] for r in self.hybrid_system))}")
        report.append(f"- **Số mối quan hệ:** {len(set(r['Relationship'] for r in self.hybrid_system))}")
        report.append(f"- **Số ngữ cảnh:** {len(set(r['Context'] for r in self.hybrid_system))}")
        report.append(f"- **Số cấp độ trang trọng:** {len(set(r['Formality_Level'] for r in self.hybrid_system))}")
        report.append(f"- **Số sắc thái cảm xúc:** {len(set(r['Emotional_Tone'] for r in self.hybrid_system))}")
        report.append("")
        
        # Thống kê theo ngữ cảnh
        context_stats = {}
        for rule in self.hybrid_system:
            context = rule['Context']
            context_stats[context] = context_stats.get(context, 0) + 1
        
        report.append("## Thống kê theo ngữ cảnh:")
        for context, count in sorted(context_stats.items()):
            report.append(f"- **{context}:** {count:,} quy tắc")
        report.append("")
        
        # Thống kê theo cấp độ trang trọng
        formality_stats = {}
        for rule in self.hybrid_system:
            formality = rule['Formality_Level']
            formality_stats[formality] = formality_stats.get(formality, 0) + 1
        
        report.append("## Thống kê theo cấp độ trang trọng:")
        for formality, count in sorted(formality_stats.items()):
            report.append(f"- **{formality}:** {count:,} quy tắc")
        report.append("")
        
        # Thống kê theo sắc thái cảm xúc
        emotion_stats = {}
        for rule in self.hybrid_system:
            emotion = rule['Emotional_Tone']
            emotion_stats[emotion] = emotion_stats.get(emotion, 0) + 1
        
        report.append("## Thống kê theo sắc thái cảm xúc:")
        for emotion, count in sorted(emotion_stats.items()):
            report.append(f"- **{emotion}:** {count:,} quy tắc")
        report.append("")
        
        report.append("## Ưu điểm của hệ thống lai:")
        report.append("1. **Kết hợp ưu điểm của cả hai hệ thống**")
        report.append("2. **Có cấu trúc rõ ràng và chi tiết**")
        report.append("3. **Bao gồm thông tin ngữ cảnh, cảm xúc, tần suất**")
        report.append("4. **Có độ ưu tiên để lựa chọn đại từ phù hợp**")
        report.append("5. **Dễ dàng tích hợp vào hệ thống dịch thuật**")
        report.append("")
        
        report.append("## Cách sử dụng:")
        report.append("1. **Sử dụng file `hybrid_pronoun_system.csv` làm cơ sở chính**")
        report.append("2. **Cập nhật PronounComplianceChecker để sử dụng hệ thống mới**")
        report.append("3. **Tích hợp vào quy trình dịch thuật tự động**")
        report.append("4. **Có thể điều chỉnh và bổ sung theo nhu cầu**")
        
        return "\n".join(report)

def main():
    """Hàm main"""
    print("🔧 Tạo hệ thống đại từ nhân xưng lai...")
    print("=" * 50)
    
    creator = HybridPronounSystemCreator()
    
    # Load dữ liệu
    print("📥 Đang load dữ liệu...")
    creator.load_data()
    
    # Tạo hệ thống lai
    print("🔬 Đang tạo hệ thống lai...")
    creator.create_hybrid_system()
    
    # Lưu hệ thống lai
    print("💾 Đang lưu hệ thống lai...")
    output_file = creator.save_hybrid_system()
    
    # Tạo báo cáo
    print("📝 Đang tạo báo cáo...")
    report = creator.generate_summary_report()
    
    with open("HYBRID_PRONOUN_SYSTEM_REPORT.md", 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ Hoàn thành! Hệ thống lai đã được lưu vào: {output_file}")
    print("📊 Báo cáo đã được lưu vào: HYBRID_PRONOUN_SYSTEM_REPORT.md")
    
    # In tóm tắt
    print("\n📈 TÓM TẮT:")
    print(f"- Tổng số quy tắc: {len(creator.hybrid_system):,}")
    print(f"- Số ngữ cảnh: {len(set(r['Context'] for r in creator.hybrid_system))}")
    print(f"- Số cấp độ trang trọng: {len(set(r['Formality_Level'] for r in creator.hybrid_system))}")
    print(f"- Số sắc thái cảm xúc: {len(set(r['Emotional_Tone'] for r in creator.hybrid_system))}")

if __name__ == "__main__":
    main()
