#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script phân tích và so sánh hai hệ thống đại từ nhân xưng
"""

import csv
import os
import sys
from collections import Counter, defaultdict

# Thêm src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.logger import setup_main_logger

logger = setup_main_logger("PronounAnalyzer")

class PronounSystemAnalyzer:
    """Phân tích và so sánh hệ thống đại từ nhân xưng"""
    
    def __init__(self):
        """Khởi tạo analyzer"""
        self.current_data = []  # Dữ liệu hiện tại từ pronoun_metadata.csv
        self.proposed_rules = []  # Quy tắc đề xuất từ bảng CSV
        self.analysis_results = {}
        
    def load_current_data(self, file_path: str = "data/metadata/pronoun_metadata.csv"):
        """Load dữ liệu hiện tại"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.current_data = list(reader)
            logger.info(f"Đã load {len(self.current_data)} dòng dữ liệu hiện tại")
        except Exception as e:
            logger.error(f"Lỗi load dữ liệu hiện tại: {e}")
    
    def load_proposed_rules(self):
        """Load quy tắc đề xuất từ bảng CSV"""
        # Dữ liệu từ bảng CSV được cung cấp
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
        
        # Parse CSV data
        lines = proposed_data.strip().split('\n')
        reader = csv.DictReader(lines)
        self.proposed_rules = list(reader)
        logger.info(f"Đã load {len(self.proposed_rules)} quy tắc đề xuất")
    
    def analyze_current_system(self):
        """Phân tích hệ thống hiện tại"""
        analysis = {
            'total_records': len(self.current_data),
            'characters': set(),
            'pronouns': set(),
            'contexts': set(),
            'relationships': set(),
            'formality_levels': set(),
            'emotional_tones': set(),
            'scene_types': set(),
            'genders': set(),
            'age_groups': set(),
            'social_statuses': set(),
            'suggested_pronouns': set(),
            'frequency_distribution': Counter(),
            'character_pronoun_mapping': defaultdict(list),
            'context_pronoun_mapping': defaultdict(list)
        }
        
        for record in self.current_data:
            # Basic info
            analysis['characters'].add(record.get('Character_Name', ''))
            analysis['pronouns'].add(record.get('Pronoun_CN', ''))
            analysis['contexts'].add(record.get('Pronoun_Context', ''))
            analysis['relationships'].add(record.get('Speaker_Relationship', ''))
            analysis['formality_levels'].add(record.get('Formality_Level', ''))
            analysis['emotional_tones'].add(record.get('Emotional_Tone', ''))
            analysis['scene_types'].add(record.get('Scene_Type', ''))
            analysis['genders'].add(record.get('Gender', ''))
            analysis['age_groups'].add(record.get('Age_Group', ''))
            analysis['social_statuses'].add(record.get('Social_Status', ''))
            analysis['suggested_pronouns'].add(record.get('Suggested_VN_Pronoun', ''))
            
            # Frequency
            freq = record.get('Frequency', '')
            analysis['frequency_distribution'][freq] += 1
            
            # Mappings
            char = record.get('Character_Name', '')
            pronoun = record.get('Suggested_VN_Pronoun', '')
            context = record.get('Pronoun_Context', '')
            
            if char and pronoun:
                analysis['character_pronoun_mapping'][char].append(pronoun)
            if context and pronoun:
                analysis['context_pronoun_mapping'][context].append(pronoun)
        
        self.analysis_results['current'] = analysis
        return analysis
    
    def analyze_proposed_system(self):
        """Phân tích hệ thống đề xuất"""
        analysis = {
            'total_rules': len(self.proposed_rules),
            'gender_groups': set(),
            'object_types': set(),
            'grammatical_persons': set(),
            'relationships': set(),
            'pronoun_forms': set(),
            'examples': set(),
            'gender_object_mapping': defaultdict(list),
            'relationship_pronoun_mapping': defaultdict(list)
        }
        
        for rule in self.proposed_rules:
            # Basic info
            analysis['gender_groups'].add(rule.get('Nhóm Giới Tính', ''))
            analysis['object_types'].add(rule.get('Đối Tượng Được Nhắc Tới', ''))
            analysis['grammatical_persons'].add(rule.get('Ngôi/Số', ''))
            analysis['relationships'].add(rule.get('Mối Quan Hệ (Người nói -> Người được nhắc tới)', ''))
            
            # Pronoun forms
            pronoun_forms = rule.get('Cách Gọi (Đại từ/Danh xưng)', '')
            if pronoun_forms:
                forms = [form.strip() for form in pronoun_forms.split('+') if form.strip()]
                analysis['pronoun_forms'].update(forms)
            
            # Examples
            example = rule.get('Ví Dụ Cụ Thể', '')
            if example:
                analysis['examples'].add(example)
            
            # Mappings
            gender = rule.get('Nhóm Giới Tính', '')
            object_type = rule.get('Đối Tượng Được Nhắc Tới', '')
            relationship = rule.get('Mối Quan Hệ (Người nói -> Người được nhắc tới)', '')
            
            if gender and object_type:
                analysis['gender_object_mapping'][f"{gender}_{object_type}"].append(pronoun_forms)
            if relationship and pronoun_forms:
                analysis['relationship_pronoun_mapping'][relationship].append(pronoun_forms)
        
        self.analysis_results['proposed'] = analysis
        return analysis
    
    def compare_systems(self):
        """So sánh hai hệ thống"""
        comparison = {
            'coverage_analysis': {},
            'complexity_analysis': {},
            'consistency_analysis': {},
            'recommendations': []
        }
        
        current = self.analysis_results['current']
        proposed = self.analysis_results['proposed']
        
        # Coverage analysis
        comparison['coverage_analysis'] = {
            'current_records': current['total_records'],
            'proposed_rules': proposed['total_rules'],
            'current_characters': len(current['characters']),
            'proposed_gender_groups': len(proposed['gender_groups']),
            'current_contexts': len(current['contexts']),
            'proposed_relationships': len(proposed['relationships'])
        }
        
        # Complexity analysis
        comparison['complexity_analysis'] = {
            'current_pronouns': len(current['suggested_pronouns']),
            'proposed_pronouns': len(proposed['pronoun_forms']),
            'current_relationships': len(current['relationships']),
            'proposed_relationships': len(proposed['relationships']),
            'current_formality_levels': len(current['formality_levels']),
            'current_emotional_tones': len(current['emotional_tones'])
        }
        
        # Consistency analysis
        comparison['consistency_analysis'] = {
            'current_has_unknown': 'unknown' in current['relationships'] or 'unknown' in current['formality_levels'],
            'proposed_has_specific_relationships': len([r for r in proposed['relationships'] if r and 'unknown' not in r]),
            'current_has_frequency_data': len(current['frequency_distribution']) > 0,
            'proposed_has_examples': len(proposed['examples']) > 0
        }
        
        # Recommendations
        recommendations = []
        
        if comparison['coverage_analysis']['proposed_rules'] < comparison['coverage_analysis']['current_records']:
            recommendations.append("Hệ thống đề xuất có ít quy tắc hơn dữ liệu hiện tại - có thể cần bổ sung")
        
        if comparison['complexity_analysis']['proposed_pronouns'] > comparison['complexity_analysis']['current_pronouns']:
            recommendations.append("Hệ thống đề xuất có nhiều đại từ hơn - phong phú hơn nhưng có thể phức tạp")
        
        if comparison['consistency_analysis']['proposed_has_specific_relationships']:
            recommendations.append("Hệ thống đề xuất có mối quan hệ cụ thể hơn - tốt hơn cho tính nhất quán")
        
        if comparison['consistency_analysis']['current_has_unknown']:
            recommendations.append("Hệ thống hiện tại có nhiều 'unknown' - cần cải thiện")
        
        comparison['recommendations'] = recommendations
        
        self.analysis_results['comparison'] = comparison
        return comparison
    
    def generate_report(self):
        """Tạo báo cáo phân tích"""
        report = []
        
        report.append("# BÁO CÁO PHÂN TÍCH HỆ THỐNG ĐẠI TỪ NHÂN XƯNG")
        report.append("=" * 60)
        report.append("")
        
        # Current system analysis
        current = self.analysis_results['current']
        report.append("## 1. HỆ THỐNG HIỆN TẠI (pronoun_metadata.csv)")
        report.append(f"- **Tổng số bản ghi:** {current['total_records']:,}")
        report.append(f"- **Số nhân vật:** {len(current['characters'])}")
        report.append(f"- **Số đại từ đề xuất:** {len(current['suggested_pronouns'])}")
        report.append(f"- **Số ngữ cảnh:** {len(current['contexts'])}")
        report.append(f"- **Số mối quan hệ:** {len(current['relationships'])}")
        report.append(f"- **Số cấp độ trang trọng:** {len(current['formality_levels'])}")
        report.append(f"- **Số sắc thái cảm xúc:** {len(current['emotional_tones'])}")
        report.append("")
        
        # Proposed system analysis
        proposed = self.analysis_results['proposed']
        report.append("## 2. HỆ THỐNG ĐỀ XUẤT (Bảng quy tắc CSV)")
        report.append(f"- **Tổng số quy tắc:** {proposed['total_rules']}")
        report.append(f"- **Số nhóm giới tính:** {len(proposed['gender_groups'])}")
        report.append(f"- **Số loại đối tượng:** {len(proposed['object_types'])}")
        report.append(f"- **Số mối quan hệ:** {len(proposed['relationships'])}")
        report.append(f"- **Số dạng đại từ:** {len(proposed['pronoun_forms'])}")
        report.append(f"- **Số ví dụ cụ thể:** {len(proposed['examples'])}")
        report.append("")
        
        # Comparison
        comparison = self.analysis_results['comparison']
        report.append("## 3. SO SÁNH HAI HỆ THỐNG")
        report.append("")
        
        report.append("### 3.1 Phân tích độ phủ sóng:")
        coverage = comparison['coverage_analysis']
        report.append(f"- **Bản ghi hiện tại vs Quy tắc đề xuất:** {coverage['current_records']:,} vs {coverage['proposed_rules']}")
        report.append(f"- **Nhân vật hiện tại vs Nhóm giới tính đề xuất:** {coverage['current_characters']} vs {coverage['proposed_gender_groups']}")
        report.append(f"- **Ngữ cảnh hiện tại vs Mối quan hệ đề xuất:** {coverage['current_contexts']} vs {coverage['proposed_relationships']}")
        report.append("")
        
        report.append("### 3.2 Phân tích độ phức tạp:")
        complexity = comparison['complexity_analysis']
        report.append(f"- **Đại từ hiện tại vs Đại từ đề xuất:** {complexity['current_pronouns']} vs {complexity['proposed_pronouns']}")
        report.append(f"- **Mối quan hệ hiện tại vs Mối quan hệ đề xuất:** {complexity['current_relationships']} vs {complexity['proposed_relationships']}")
        report.append(f"- **Cấp độ trang trọng hiện tại:** {complexity['current_formality_levels']}")
        report.append(f"- **Sắc thái cảm xúc hiện tại:** {complexity['current_emotional_tones']}")
        report.append("")
        
        report.append("### 3.3 Phân tích tính nhất quán:")
        consistency = comparison['consistency_analysis']
        report.append(f"- **Hệ thống hiện tại có 'unknown':** {'Có' if consistency['current_has_unknown'] else 'Không'}")
        report.append(f"- **Hệ thống đề xuất có mối quan hệ cụ thể:** {'Có' if consistency['proposed_has_specific_relationships'] else 'Không'}")
        report.append(f"- **Hệ thống hiện tại có dữ liệu tần suất:** {'Có' if consistency['current_has_frequency_data'] else 'Không'}")
        report.append(f"- **Hệ thống đề xuất có ví dụ cụ thể:** {'Có' if consistency['proposed_has_examples'] else 'Không'}")
        report.append("")
        
        # Recommendations
        report.append("## 4. KHUYẾN NGHỊ")
        report.append("")
        
        for i, rec in enumerate(comparison['recommendations'], 1):
            report.append(f"{i}. {rec}")
        report.append("")
        
        # Detailed analysis
        report.append("## 5. PHÂN TÍCH CHI TIẾT")
        report.append("")
        
        report.append("### 5.1 Điểm mạnh của hệ thống đề xuất:")
        report.append("- **Có cấu trúc rõ ràng:** Phân loại theo giới tính, đối tượng, mối quan hệ")
        report.append("- **Có ví dụ cụ thể:** Giúp hiểu rõ cách sử dụng")
        report.append("- **Có nhiều lựa chọn đại từ:** Phong phú hơn hệ thống hiện tại")
        report.append("- **Có mối quan hệ cụ thể:** Không có 'unknown' như hệ thống hiện tại")
        report.append("")
        
        report.append("### 5.2 Điểm yếu của hệ thống đề xuất:")
        report.append("- **Ít quy tắc hơn dữ liệu hiện tại:** Có thể không đủ chi tiết")
        report.append("- **Không có dữ liệu tần suất:** Không biết đại từ nào được dùng nhiều")
        report.append("- **Không có thông tin ngữ cảnh:** Thiếu thông tin về tường thuật/hội thoại")
        report.append("- **Không có thông tin cảm xúc:** Thiếu sắc thái cảm xúc")
        report.append("")
        
        report.append("### 5.3 Kết luận:")
        report.append("**CÓ THỂ sử dụng bảng quy tắc đề xuất làm nguyên tắc chung**, nhưng cần:")
        report.append("1. **Bổ sung thông tin ngữ cảnh** (tường thuật/hội thoại)")
        report.append("2. **Bổ sung thông tin cảm xúc** (tôn trọng/khinh miệt/thân mật)")
        report.append("3. **Bổ sung dữ liệu tần suất** để biết đại từ nào phổ biến")
        report.append("4. **Tích hợp với dữ liệu hiện tại** để có thông tin đầy đủ")
        report.append("")
        
        report.append("### 5.4 Đề xuất triển khai:")
        report.append("1. **Sử dụng bảng quy tắc làm cơ sở chính** cho hệ thống đại từ")
        report.append("2. **Bổ sung thông tin từ dữ liệu hiện tại** (ngữ cảnh, cảm xúc, tần suất)")
        report.append("3. **Tạo hệ thống lai** kết hợp ưu điểm của cả hai")
        report.append("4. **Cập nhật PronounComplianceChecker** để sử dụng hệ thống mới")
        report.append("")
        
        return "\n".join(report)
    
    def save_analysis(self, output_file: str = "PRONOUN_SYSTEM_ANALYSIS.md"):
        """Lưu báo cáo phân tích"""
        report = self.generate_report()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Đã lưu báo cáo phân tích vào {output_file}")
        return output_file

def main():
    """Hàm main"""
    print("🔍 Phân tích hệ thống đại từ nhân xưng...")
    print("=" * 50)
    
    analyzer = PronounSystemAnalyzer()
    
    # Load dữ liệu
    print("📥 Đang load dữ liệu...")
    analyzer.load_current_data()
    analyzer.load_proposed_rules()
    
    # Phân tích
    print("🔬 Đang phân tích hệ thống hiện tại...")
    analyzer.analyze_current_system()
    
    print("🔬 Đang phân tích hệ thống đề xuất...")
    analyzer.analyze_proposed_system()
    
    print("⚖️ Đang so sánh hai hệ thống...")
    analyzer.compare_systems()
    
    # Tạo báo cáo
    print("📝 Đang tạo báo cáo...")
    output_file = analyzer.save_analysis()
    
    print(f"✅ Hoàn thành! Báo cáo đã được lưu vào: {output_file}")
    
    # In tóm tắt
    comparison = analyzer.analysis_results['comparison']
    print("\n📊 TÓM TẮT:")
    print(f"- Hệ thống hiện tại: {comparison['coverage_analysis']['current_records']:,} bản ghi")
    print(f"- Hệ thống đề xuất: {comparison['coverage_analysis']['proposed_rules']} quy tắc")
    print(f"- Số khuyến nghị: {len(comparison['recommendations'])}")
    
    print("\n🎯 KẾT LUẬN: CÓ THỂ sử dụng bảng quy tắc đề xuất làm nguyên tắc chung!")

if __name__ == "__main__":
    main()
