#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tạo file CSV chuẩn từ bảng quy tắc đề xuất
"""

import csv
import os
import sys

# Thêm src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.logger import setup_main_logger

logger = setup_main_logger("StandardPronounRules")

class StandardPronounRulesCreator:
    """Tạo file CSV chuẩn từ bảng quy tắc đề xuất"""
    
    def __init__(self):
        """Khởi tạo creator"""
        self.pronoun_rules = []
        
    def create_standard_rules(self):
        """Tạo quy tắc chuẩn từ bảng đề xuất"""
        
        # Dữ liệu từ bảng quy tắc đề xuất
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
        
        # Parse dữ liệu
        lines = proposed_data.strip().split('\n')
        reader = csv.DictReader(lines)
        raw_rules = list(reader)
        
        # Tạo quy tắc chuẩn với thông tin bổ sung
        for rule in raw_rules:
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
            
            # Tạo quy tắc cho các ngữ cảnh khác nhau
            contexts = ['narration', 'dialogue', 'internal_monologue']
            emotional_tones = ['neutral', 'respectful', 'affectionate', 'contemptuous', 'angry', 'playful']
            frequencies = ['High', 'Medium', 'Low']
            
            for context in contexts:
                for emotion in emotional_tones:
                    # Chọn đại từ phù hợp với ngữ cảnh và cảm xúc
                    selected_pronouns = self._select_pronouns_for_context_emotion(
                        pronouns, context, emotion, gender_group, object_type
                    )
                    
                    if selected_pronouns:
                        # Xác định tần suất
                        frequency = self._determine_frequency(relationship, context, emotion)
                        
                        # Tạo quy tắc
                        standard_rule = {
                            'Gender_Group': gender_group,
                            'Object_Type': object_type,
                            'Grammatical_Person': grammatical_person,
                            'Relationship': relationship,
                            'Context': context,
                            'Emotional_Tone': emotion,
                            'Frequency': frequency,
                            'Primary_Pronoun': selected_pronouns[0] if selected_pronouns else '',
                            'Alternative_Pronouns': '|'.join(selected_pronouns[1:]) if len(selected_pronouns) > 1 else '',
                            'All_Pronouns': '|'.join(pronouns),
                            'Example': example,
                            'Usage_Rule': self._generate_usage_rule(relationship, context, emotion),
                            'Priority': self._calculate_priority(relationship, context, emotion)
                        }
                        
                        self.pronoun_rules.append(standard_rule)
        
        logger.info(f"Đã tạo {len(self.pronoun_rules)} quy tắc chuẩn")
    
    def _select_pronouns_for_context_emotion(self, pronouns, context, emotion, gender_group, object_type):
        """Chọn đại từ phù hợp với ngữ cảnh và cảm xúc"""
        selected = []
        
        # Mapping cơ bản theo ngữ cảnh
        context_mapping = {
            'narration': ['hắn', 'nàng', 'anh', 'cô', 'chàng', 'nàng', 'ông', 'bà', 'gã', 'ả', 'nó'],
            'dialogue': ['anh', 'cô', 'cậu', 'nàng', 'chàng', 'nàng', 'ông', 'bà', 'ngài'],
            'internal_monologue': ['hắn', 'nàng', 'anh', 'cô', 'cậu', 'nàng', 'gã', 'ả']
        }
        
        # Mapping theo cảm xúc
        emotion_mapping = {
            'respectful': ['anh', 'cô', 'ông', 'bà', 'ngài', 'sư phụ', 'sư tôn'],
            'affectionate': ['chàng', 'nàng', 'anh', 'em', 'bảo bối', 'tiểu yêu tinh'],
            'contemptuous': ['hắn', 'gã', 'ả', 'nó', 'tiểu tử', 'thằng nhãi'],
            'angry': ['hắn', 'gã', 'ả', 'nó', 'tên kia', 'lão quỷ'],
            'playful': ['cậu', 'nàng', 'anh', 'em', 'tiểu tử'],
            'neutral': ['anh', 'cô', 'hắn', 'nàng', 'gã', 'ả']
        }
        
        # Lọc đại từ dựa trên ngữ cảnh và cảm xúc
        context_pronouns = context_mapping.get(context, pronouns)
        emotion_pronouns = emotion_mapping.get(emotion, pronouns)
        
        # Tìm giao điểm
        for pronoun in pronouns:
            if (pronoun in context_pronouns and pronoun in emotion_pronouns):
                selected.append(pronoun)
        
        # Nếu không có giao điểm, lấy đại từ phù hợp nhất
        if not selected:
            if context == 'narration':
                selected = [p for p in pronouns if p in ['hắn', 'nàng', 'anh', 'cô', 'gã', 'ả']]
            elif context == 'dialogue':
                selected = [p for p in pronouns if p in ['anh', 'cô', 'cậu', 'nàng', 'ông', 'bà']]
            else:
                selected = pronouns[:2]
        
        return selected[:3]  # Tối đa 3 đại từ
    
    def _determine_frequency(self, relationship, context, emotion):
        """Xác định tần suất sử dụng"""
        # Tần suất cao cho các mối quan hệ phổ biến
        high_freq_relationships = [
            'Tác Giả Tường Thuật', 'Nam chính', 'Nữ chính', 'Sư phụ', 'Sư huynh', 'Sư đệ'
        ]
        
        if any(rel in relationship for rel in high_freq_relationships):
            return 'High'
        elif context == 'narration' and emotion == 'neutral':
            return 'High'
        else:
            return 'Medium'
    
    def _generate_usage_rule(self, relationship, context, emotion):
        """Tạo quy tắc sử dụng"""
        rules = []
        
        if context == 'narration':
            rules.append("Sử dụng trong tường thuật")
        elif context == 'dialogue':
            rules.append("Sử dụng trong hội thoại")
        elif context == 'internal_monologue':
            rules.append("Sử dụng trong nội tâm")
        
        if emotion == 'respectful':
            rules.append("Thể hiện sự tôn trọng")
        elif emotion == 'affectionate':
            rules.append("Thể hiện sự thân mật")
        elif emotion == 'contemptuous':
            rules.append("Thể hiện sự khinh miệt")
        elif emotion == 'angry':
            rules.append("Thể hiện sự tức giận")
        elif emotion == 'playful':
            rules.append("Thể hiện sự vui đùa")
        
        return "; ".join(rules)
    
    def _calculate_priority(self, relationship, context, emotion):
        """Tính độ ưu tiên"""
        priority = 0
        
        # Ngữ cảnh
        if context == 'narration':
            priority += 3
        elif context == 'dialogue':
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
        
        # Mối quan hệ
        if 'Tác Giả Tường Thuật' in relationship:
            priority += 3
        elif 'Sư phụ' in relationship or 'Sư huynh' in relationship:
            priority += 2
        else:
            priority += 1
        
        return priority
    
    def save_standard_rules(self, output_file: str = "data/metadata/standard_pronoun_rules.csv"):
        """Lưu quy tắc chuẩn"""
        if not self.pronoun_rules:
            logger.warning("Không có dữ liệu để lưu")
            return
        
        # Sắp xếp theo độ ưu tiên
        self.pronoun_rules.sort(key=lambda x: x['Priority'], reverse=True)
        
        # Lưu file CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'Gender_Group', 'Object_Type', 'Grammatical_Person', 'Relationship',
                'Context', 'Emotional_Tone', 'Frequency', 'Primary_Pronoun',
                'Alternative_Pronouns', 'All_Pronouns', 'Example', 'Usage_Rule', 'Priority'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.pronoun_rules)
        
        logger.info(f"Đã lưu {len(self.pronoun_rules)} quy tắc chuẩn vào {output_file}")
        return output_file

def main():
    """Hàm main"""
    print("🔧 Tạo quy tắc đại từ nhân xưng chuẩn...")
    print("=" * 50)
    
    creator = StandardPronounRulesCreator()
    
    # Tạo quy tắc chuẩn
    print("📝 Đang tạo quy tắc chuẩn...")
    creator.create_standard_rules()
    
    # Lưu quy tắc
    print("💾 Đang lưu quy tắc...")
    output_file = creator.save_standard_rules()
    
    print(f"✅ Hoàn thành! Quy tắc chuẩn đã được lưu vào: {output_file}")
    print(f"📊 Tổng số quy tắc: {len(creator.pronoun_rules):,}")

if __name__ == "__main__":
    main()
