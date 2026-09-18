import hashlib
from datetime import datetime, timedelta

from ezticketapp import db, app
from ezticketapp.models import (
    User, EventType, TicketType, PaymentMethod,
    Event, EventTicket, Voucher, Order, OrderItem, EventReport,
    CustomerProfile, Role, Gender, OrderStatus,
)

PWD_HASH = hashlib.md5("123".encode("utf-8")).hexdigest()


def create_sample_data():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Neo thời gian chạy script: mọi mốc ngày giờ quá khứ và tương lai đều tính tương đối theo mốc này
        base_now = datetime.now().replace(microsecond=0, second=0)

        def rel_days(days, hour=19, minute=30):
            """Tính thời gian tương đối theo ngày so với thời điểm chạy script."""
            return (base_now + timedelta(days=days)).replace(hour=hour, minute=minute)

        def rel_years(year_offset, month, day, hour=19, minute=30):
            """Tính thời gian tương đối theo năm để phục vụ lọc theo năm (2024, 2025, 2026, ...)."""
            target_year = base_now.year + year_offset
            try:
                return datetime(target_year, month, day, hour, minute)
            except ValueError:
                return datetime(target_year, month, day - 1, hour, minute)

        # ===================== 1. EVENT TYPES =====================
        event_types = [
            EventType(name="Bóng đá"),     # 0
            EventType(name="Điện tử"),     # 1
            EventType(name="Hội thảo"),    # 2
            EventType(name="Âm nhạc"),     # 3
            EventType(name="Công nghệ"),   # 4
        ]
        db.session.add_all(event_types)
        db.session.flush()

        # ===================== 2. TICKET TYPES =====================
        ticket_types = [
            TicketType(name="Thường"),     # 0
            TicketType(name="VIP"),        # 1
            TicketType(name="VIP Pro"),    # 2
        ]
        db.session.add_all(ticket_types)
        db.session.flush()

        # ===================== 3. PAYMENT METHODS =====================
        payment_methods = [
            PaymentMethod(name="MoMo"),     # 0
            PaymentMethod(name="ZaloPay"),  # 1
            PaymentMethod(name="VNPay"),    # 2
        ]
        db.session.add_all(payment_methods)
        db.session.flush()

        # ===================== 4. USERS =====================
        avatar_admin = "https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg"
        avatar_org = "https://res.cloudinary.com/dpxsbyyey/image/upload/v1775650754/avatar_user_nzinrm.webp"
        avatar_cus = "https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg"

        users = [
            # 0: Admin
            User(full_name="Admin EzTicket", email="admin@example.com",
                 password=PWD_HASH, role=Role.ADMIN, active=True, avatar=avatar_admin),

            # 1..3: Active Organizers
            User(full_name="Nguyễn Văn An", email="nguyenvan@ezticket.com",
                 password=PWD_HASH, role=Role.ORGANIZER, active=True, avatar=avatar_org),
            User(full_name="Trần Thị Bình", email="tranthib@ezticket.com",
                 password=PWD_HASH, role=Role.ORGANIZER, active=True, avatar=avatar_org),
            User(full_name="Lê Minh Chí", email="leminh@ezticket.com",
                 password=PWD_HASH, role=Role.ORGANIZER, active=True, avatar=avatar_org),

            # 4: Inactive Organizer (để test chức năng khóa/mở tài khoản của Admin)
            User(full_name="Công Ty Tổ Chức Bị Khóa", email="khoa_org@ezticket.com",
                 password=PWD_HASH, role=Role.ORGANIZER, active=False, avatar=avatar_org),

            # 5..12: Active Customers
            User(full_name="Hoàng Thị Vy", email="hoangvy@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER, active=True, avatar=avatar_cus),
            User(full_name="Thanh Sơn", email="thanhson@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER, active=True, avatar=avatar_cus),
            User(full_name="Phương Anh", email="phuonganh@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER, active=True, avatar=avatar_cus),
            User(full_name="Đức Trung", email="ductrung@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER, active=True, avatar=avatar_cus),
            User(full_name="Minh Châu", email="minhchau@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER, active=True, avatar=avatar_cus),
            User(full_name="Quốc Đạt", email="quocdat@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER, active=True, avatar=avatar_cus),
            User(full_name="Thùy My", email="thuymy@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER, active=True, avatar=avatar_cus),
            User(full_name="Văn Hậu", email="vanhau@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER, active=True, avatar=avatar_cus),

            # 13: Inactive Customer (test tài khoản bị khóa)
            User(full_name="Khách Hàng Bị Khóa", email="khoa_cus@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER, active=False, avatar=avatar_cus),
        ]
        db.session.add_all(users)
        db.session.flush()

        # ===================== 5. CUSTOMER PROFILES =====================
        # Phủ đầy đủ 5 danh mục sở thích để test đề xuất sự kiện theo Customer
        profiles = [
            CustomerProfile(user_id=users[5].id, gender=Gender.FEMALE, preferred_event_type_id=event_types[3].id),  # Âm nhạc
            CustomerProfile(user_id=users[6].id, gender=Gender.MALE,   preferred_event_type_id=event_types[0].id),  # Bóng đá
            CustomerProfile(user_id=users[7].id, gender=Gender.FEMALE, preferred_event_type_id=event_types[2].id),  # Hội thảo
            CustomerProfile(user_id=users[8].id, gender=Gender.MALE,   preferred_event_type_id=event_types[1].id),  # Điện tử
            CustomerProfile(user_id=users[9].id, gender=Gender.FEMALE, preferred_event_type_id=event_types[4].id),  # Công nghệ
            CustomerProfile(user_id=users[10].id, gender=Gender.MALE,  preferred_event_type_id=event_types[0].id),  # Bóng đá
            CustomerProfile(user_id=users[11].id, gender=Gender.FEMALE, preferred_event_type_id=event_types[3].id), # Âm nhạc
            CustomerProfile(user_id=users[12].id, gender=Gender.MALE,  preferred_event_type_id=event_types[1].id),  # Điện tử
            CustomerProfile(user_id=users[13].id, gender=Gender.OTHER, preferred_event_type_id=event_types[4].id),  # Công nghệ
        ]
        db.session.add_all(profiles)
        db.session.flush()

        # ===================== 6. EVENTS =====================
        img = "https://images.unsplash.com/photo-"

        # (name, location, image, purchase_limit, cancel_hours, time, etype_idx, org_idx, is_active)
        events_data = [
            # -----------------------------------------------------------------------------------------
            # NHÓM 1: ORGANIZER 1 (Nguyễn Văn An - users[1]) - TƯƠNG LAI
            # -----------------------------------------------------------------------------------------
            # 0: Gợi ý 30% (còn 3 ngày nữa, remaining > 30%)
            ("Đêm Nhạc Pop-Rock Acoustic", "Nhà thi đấu Phú Thọ, TP.HCM",
             img + "1501386761578-eac5c94b800a", 4, 24, rel_days(3, 19, 30), 3, 1, True),
            # 1: Gợi ý 30% (còn 5 ngày nữa, remaining > 30%)
            ("Đêm Nhạc EDM Electric Beat", "Beach Bar, TP. Nha Trang",
             img + "1470225619355-5c5c2f0446eb", 5, 24, rel_days(5, 20, 0), 3, 1, True),
            # 2: Gợi ý 15% (còn 12 ngày nữa, remaining > 30%)
            ("Giải Bóng Đá Cúp Thành Phố", "Sân vận động Thống Nhất, TP.HCM",
             img + "1552674605-db6ffd4facb5", 5, 24, rel_days(12, 16, 0), 0, 1, True),
            # 3: Gợi ý 15% (còn 16 ngày nữa, chưa bán vé nào 100%)
            ("Liveshow Symphony & Jazz", "Nhà hát Lớn Hà Nội",
             img + "1514320291840-2e0a9bf2a9ae", 4, 24, rel_days(16, 19, 30), 3, 1, True),
            # 4: Đối chứng: Tương lai gần (+4 ngày) nhưng vé bán chạy (chỉ còn 15% vé) -> KHÔNG gợi ý
            ("Marathon TP.HCM City Run", "Quận 1, TP.HCM",
             img + "1552674605-db6ffd4facb5", 2, 48, rel_days(4, 5, 30), 0, 1, True),
            # 5: Đối chứng: Tương lai xa (+45 ngày > 20 ngày) -> KHÔNG gợi ý
            ("Đêm Nhạc Mùa Hè Rực Rỡ", "Công viên Biển Đông, Đà Nẵng",
             img + "1493225457124-a3eb161ffa5f", 6, 24, rel_days(45, 20, 0), 3, 1, True),
            # 6: Chưa bán vé nào -> Dành riêng để Org 1 test chức năng Xóa sự kiện!
            ("Giải Bóng Đá Mini Giao Hữu", "Sân QK7, TP.HCM",
             img + "1431324155629-1a6deb1dec8d", 4, 24, rel_days(25, 17, 0), 0, 1, True),

            # -----------------------------------------------------------------------------------------
            # NHÓM 2: ORGANIZER 2 (Trần Thị Bình - users[2]) - TƯƠNG LAI
            # -----------------------------------------------------------------------------------------
            # 7: Gợi ý 30% (còn 4 ngày nữa, remaining > 30%)
            ("Workshop Generative AI 2026", "SECC Quận 7, TP.HCM",
             img + "1485827404703-89b55fcc595e", 3, 12, rel_days(4, 8, 30), 4, 2, True),
            # 8: Gợi ý 30% (còn 7 ngày nữa, remaining > 30%)
            ("Hội Thảo Digital Transformation", "Pullman Hotel, TP.HCM",
             img + "1540575467063-178a50c2df87", 4, 24, rel_days(7, 8, 30), 2, 2, True),
            # 9: Gợi ý 15% (còn 11 ngày nữa, remaining > 30%)
            ("Khóa Đào Tạo DevOps & Cloud", "ĐH FPT, Hà Nội",
             img + "1515879218367-8466d910aaa4", 3, 24, rel_days(11, 9, 0), 4, 2, True),
            # 10: Gợi ý 15% (còn 18 ngày nữa, chưa bán vé nào 100%)
            ("Tech Talk Blockchain & Web3", "Khách sạn Rex, TP.HCM",
             img + "1519389359179-57921414cf25", 3, 24, rel_days(18, 8, 30), 4, 2, True),
            # 11: Đối chứng: Tương lai gần (+3 ngày) nhưng vé bán chạy (chỉ còn 10% vé) -> KHÔNG gợi ý
            ("Workshop Cybersecurity Chuyên Sâu", "ĐH Bách Khoa, TP.HCM",
             img + "1550751827-4bd374c3f58b", 2, 12, rel_days(3, 8, 30), 4, 2, True),
            # 12: Đối chứng: Tương lai xa (+60 ngày > 20 ngày) -> KHÔNG gợi ý
            ("AI Summit Quốc Tế", "JW Marriott, Hà Nội",
             img + "1475721027785-f74eccf877e2", 5, 24, rel_days(60, 8, 0), 4, 2, True),
            # 13: Chưa bán vé nào -> Dành riêng để Org 2 test chức năng Xóa sự kiện!
            ("Hội Thảo Khởi Nghiệp Startup & Tech", "Lotte Hotel, Hà Nội",
             img + "1475721027785-f74eccf877e2", 3, 24, rel_days(30, 8, 0), 2, 2, True),

            # -----------------------------------------------------------------------------------------
            # NHÓM 3: ORGANIZER 3 (Lê Minh Chí - users[3]) - TƯƠNG LAI
            # -----------------------------------------------------------------------------------------
            # 14: Gợi ý 30% (còn 2 ngày nữa, remaining > 30%)
            ("Chung Kết eSports Tournament", "Nhà thi đấu Tân Bình, TP.HCM",
             img + "1542751371-adc38448a05e", 6, 48, rel_days(2, 13, 0), 1, 3, True),
            # 15: Gợi ý 30% (còn 6 ngày nữa, remaining > 30%)
            ("Triển Lãm Đồ Họa & Game Design", "Trung tâm Hội chợ TP.HCM",
             img + "1542751371-adc38448a05e", 5, 24, rel_days(6, 9, 0), 1, 3, True),
            # 16: Gợi ý 15% (còn 14 ngày nữa, remaining > 30%)
            ("Hội Chợ Công Nghệ Tiêu Dùng", "SECC Quận 7, TP.HCM",
             img + "1475721027785-f74eccf877e2", 8, 48, rel_days(14, 9, 0), 2, 3, True),
            # 17: Gợi ý 15% (còn 19 ngày nữa, chưa bán vé nào 100%)
            ("Lễ Trao Giải Sáng Tạo Nội Dung", "Nhà hát Lớn TP.HCM",
             img + "1542751371-adc38448a05e", 5, 48, rel_days(19, 19, 0), 1, 3, True),
            # 18: Đối chứng: Tương lai gần (+5 ngày) nhưng vé bán chạy (chỉ còn 12% vé) -> KHÔNG gợi ý
            ("Giải Đấu Mobile Gaming Pro", "Nhà thi đấu QK7, TP.HCM",
             img + "1542751371-adc38448a05e", 4, 24, rel_days(5, 13, 0), 1, 3, True),
            # 19: Đối chứng: Tương lai xa (+90 ngày > 20 ngày) -> KHÔNG gợi ý
            ("Triển Lãm Metaverse & XR", "The Factory, TP.HCM",
             img + "1558618666-fcd25c85f7e7", 4, 24, rel_days(90, 10, 0), 1, 3, True),
            # 20: Chưa bán vé nào -> Dành riêng để Org 3 test chức năng Xóa sự kiện!
            ("Lễ Hội Ẩm Thực & Văn Hóa Sinh Viên", "Công viên Gia Định, TP.HCM",
             img + "1555939594-58d7cb561ad1", 10, 48, rel_days(35, 9, 0), 2, 3, True),

            # -----------------------------------------------------------------------------------------
            # NHÓM 4: SỰ KIỆN ĐẶC BIỆT & CÁC NĂM TƯƠNG LAI
            # -----------------------------------------------------------------------------------------
            # 21: Edge case - Sắp hết vé (chỉ còn đúng 2 vé)
            ("Acoustic Night Trà Chiều", "Coffee House Bùi Viện, TP.HCM",
             img + "1506157786151-b8491531f063", 4, 24, rel_days(8, 19, 0), 3, 1, True),
            # 22: Edge case - HẾT VÉ hoàn toàn (quantity = 0, ẩn khỏi trang chủ khách)
            ("Workshop Data Science Thực Hành", "ĐH Bách Khoa, TP.HCM",
             img + "1551288046-da764c7d12be", 3, 12, rel_days(10, 9, 0), 4, 2, True),
            # 23: Edge case - Sự kiện BỊ ẨN (is_active = False, test toggle active)
            ("Triển Lãm Mỹ Thuật Nghệ Sĩ Trẻ", "Bảo tàng Mỹ thuật TP.HCM",
             img + "1460661419201-fd4cecdf8a8b", 3, 12, rel_days(15, 10, 0), 2, 3, False),
            # 24: Năm tương lai: Sự kiện Countdown đón năm mới
            ("Đêm Nhạc Countdown Đón Năm Mới", "Bến Thành Square, TP.HCM",
             img + "1493225457124-a3eb161ffa5f", 8, 48, rel_days(120, 20, 0), 3, 1, True),

            # -----------------------------------------------------------------------------------------
            # NHÓM 5: SỰ KIỆN QUÁ KHỨ NĂM NAY (Phục vụ báo cáo, đánh giá, thống kê)
            # -----------------------------------------------------------------------------------------
            # 25: Diễn ra cách đây 2 ngày (có report phản ánh)
            ("Đêm Nhạc Bolero Xưa", "Nhà hát Lớn Hà Nội",
             img + "1514320291840-2e0a9bf2a9ae", 4, 24, rel_days(-2, 19, 30), 3, 1, True),
            # 26: Diễn ra cách đây 10 ngày (có report phản ánh)
            ("Workshop Python Cơ Bản Cho Người Mới", "TechHub, Hà Nội",
             img + "1515879218367-8466d910aaa4", 2, 12, rel_days(-10, 9, 0), 4, 2, True),
            # 27: Diễn ra cách đây 1 tháng (30 ngày trước)
            ("Giải Futsal Doanh Nghiệp Trẻ", "Nhà thi đấu Quân khu 7, TP.HCM",
             img + "1431324155629-1a6deb1dec8d", 5, 24, rel_days(-30, 18, 0), 0, 1, True),
            # 28: Diễn ra cách đây 2 tháng (60 ngày trước, có report)
            ("Triển Lãm Ảnh Đương Đại", "Bảo tàng Mỹ thuật, Đà Nẵng",
             img + "1460661419201-fd4cecdf8a8b", 3, 12, rel_days(-60, 10, 0), 2, 3, True),
            # 29: Diễn ra cách đây 3 tháng (90 ngày trước, test lọc theo quý trước)
            ("Hội Thảo Trí Tuệ Nhân Tạo & Robotics", "Grand Hotel, TP.HCM",
             img + "1540575467063-178a50c2df87", 3, 24, rel_days(-90, 8, 0), 4, 2, True),
            # 30: Diễn ra cách đây 5 tháng (150 ngày trước)
            ("Đêm Nhạc Rock Sôi Động", "Club MTV, TP.HCM",
             img + "1493225457124-a3eb161ffa5f", 4, 24, rel_days(-150, 21, 0), 3, 1, True),

            # -----------------------------------------------------------------------------------------
            # NHÓM 6: SỰ KIỆN 1 NĂM TRƯỚC (base_now.year - 1) - Phục vụ lọc theo năm trước
            # -----------------------------------------------------------------------------------------
            # 31
            ("Workshop AI Spring Hội Nhập", "SECC Quận 7, TP.HCM",
             img + "1485827404703-89b55fcc595e", 3, 24, rel_years(-1, 3, 15, 9, 0), 4, 2, True),
            # 32
            ("Đêm Nhạc Hạ Vàng Rực Rỡ", "Nhà thi đấu Phú Thọ, TP.HCM",
             img + "1501386761578-eac5c94b800a", 4, 24, rel_years(-1, 5, 20, 19, 30), 3, 1, True),
            # 33
            ("Giải Bóng Đá Mùa Hè Cúp Vàng", "Sân Thống Nhất, TP.HCM",
             img + "1552674605-db6ffd4facb5", 5, 24, rel_years(-1, 8, 12, 16, 0), 0, 1, True),
            # 34
            ("eSports Championship Toàn Quốc", "Nhà thi đấu Tân Bình, TP.HCM",
             img + "1542751371-adc38448a05e", 6, 48, rel_years(-1, 11, 25, 13, 0), 1, 3, True),

            # -----------------------------------------------------------------------------------------
            # NHÓM 7: SỰ KIỆN 2 NĂM TRƯỚC (base_now.year - 2) - Phục vụ lịch sử 3 năm liên tiếp
            # -----------------------------------------------------------------------------------------
            # 35
            ("Đêm Nhạc Mùa Xuân Kỷ Niệm", "Nhà thi đấu Phú Thọ, TP.HCM",
             img + "1501386761578-eac5c94b800a", 4, 24, rel_years(-2, 2, 10, 19, 30), 3, 1, True),
            # 36
            ("Giải Bóng Đá Khởi Động Mùa Xuân", "Sân Thống Nhất, TP.HCM",
             img + "1552674605-db6ffd4facb5", 5, 24, rel_years(-2, 4, 10, 16, 0), 0, 1, True),
            # 37
            ("Tech Expo Đột Phá Công Nghệ", "Bảo tàng Mỹ thuật TP.HCM",
             img + "1460661419201-fd4cecdf8a8b", 3, 12, rel_years(-2, 7, 15, 9, 0), 2, 3, True),
            # 38
            ("DevOps Summit Thường Niên", "TechHub, Hà Nội",
             img + "1515879218367-8466d910aaa4", 2, 12, rel_years(-2, 10, 20, 8, 30), 4, 2, True),
        ]

        events = []
        for (name, location, image, purchase_limit, cancel_h, time_val, etype_idx, org_idx, is_act) in events_data:
            e = Event(
                name=name, location=location, image=image,
                purchase_limit=purchase_limit, cancellation_time_limit_by_hours=cancel_h,
                time=time_val, event_type_id=event_types[etype_idx].id,
                organizer_id=users[org_idx].id, is_active=is_act
            )
            events.append(e)
        db.session.add_all(events)
        db.session.flush()

        # ===================== 7. EVENT TICKETS =====================
        # (ev_idx, tt_idx, price, remaining_quantity)
        et_tickets_data = [
            # Event 0: Đêm Nhạc Pop-Rock (Org 1 - Gợi ý 30%)
            (0, 0, 350000, 450), (0, 1, 700000, 180), (0, 2, 1200000, 40),
            # Event 1: EDM Electric Beat (Org 1 - Gợi ý 30%)
            (1, 0, 400000, 550), (1, 1, 800000, 220), (1, 2, 1500000, 50),
            # Event 2: Giải Bóng Đá Cúp TP (Org 1 - Gợi ý 15%)
            (2, 0, 120000, 900), (2, 1, 280000, 180),
            # Event 3: Liveshow Symphony & Jazz (Org 1 - Gợi ý 15%, chưa bán)
            (3, 0, 300000, 400), (3, 1, 600000, 150), (3, 2, 1200000, 30),
            # Event 4: Marathon (Org 1 - vé còn ít 15% -> KHÔNG gợi ý)
            (4, 0, 200000, 15),
            # Event 5: Đêm Nhạc Mùa Hè (+45 ngày -> KHÔNG gợi ý)
            (5, 0, 250000, 300), (5, 1, 550000, 100),
            # Event 6: Giải Bóng Đá Mini (chưa bán vé nào -> test XÓA)
            (6, 0, 80000, 200), (6, 1, 150000, 50),

            # Event 7: Workshop Generative AI (Org 2 - Gợi ý 30%)
            (7, 0, 200000, 140), (7, 1, 500000, 45),
            # Event 8: Hội Thảo Digital Transformation (Org 2 - Gợi ý 30%)
            (8, 0, 180000, 180), (8, 1, 450000, 45),
            # Event 9: DevOps & Cloud (Org 2 - Gợi ý 15%)
            (9, 0, 250000, 110), (9, 1, 600000, 25),
            # Event 10: Tech Talk Blockchain (Org 2 - Gợi ý 15%, chưa bán)
            (10, 0, 300000, 150), (10, 1, 700000, 40),
            # Event 11: Cybersecurity (Org 2 - vé chỉ còn 10% -> KHÔNG gợi ý)
            (11, 0, 250000, 10), (11, 1, 550000, 3),
            # Event 12: AI Summit (+60 ngày -> KHÔNG gợi ý)
            (12, 0, 400000, 200), (12, 1, 900000, 50),
            # Event 13: Hội Thảo Khởi Nghiệp (chưa bán vé nào -> test XÓA)
            (13, 0, 150000, 100), (13, 1, 350000, 30),

            # Event 14: eSports Tournament (Org 3 - Gợi ý 30%)
            (14, 0, 150000, 380), (14, 1, 350000, 110), (14, 2, 700000, 25),
            # Event 15: Triển Lãm Game Design (Org 3 - Gợi ý 30%)
            (15, 0, 120000, 450), (15, 1, 300000, 130), (15, 2, 600000, 35),
            # Event 16: Hội Chợ CN Tiêu Dùng (Org 3 - Gợi ý 15%)
            (16, 0, 60000, 1400), (16, 1, 200000, 380),
            # Event 17: Lễ Trao Giải Sáng Tạo (Org 3 - Gợi ý 15%, chưa bán)
            (17, 0, 150000, 500), (17, 1, 350000, 150), (17, 2, 700000, 40),
            # Event 18: Mobile Gaming Pro (Org 3 - vé còn 12% -> KHÔNG gợi ý)
            (18, 0, 100000, 12), (18, 1, 250000, 5),
            # Event 19: Triển Lãm Metaverse (+90 ngày -> KHÔNG gợi ý)
            (19, 0, 100000, 400), (19, 1, 250000, 100),
            # Event 20: Ẩm Thực Sinh Viên (chưa bán vé nào -> test XÓA)
            (20, 0, 50000, 500), (20, 1, 120000, 100),

            # Event 21: Acoustic Night (Edge case: đúng 2 vé)
            (21, 0, 180000, 2),
            # Event 22: Data Science (Edge case: hết vé 0)
            (22, 0, 200000, 0), (22, 1, 450000, 0),
            # Event 23: Triển Lãm Nghệ Sĩ Trẻ (Ẩn)
            (23, 0, 80000, 200), (23, 1, 200000, 50),
            # Event 24: Countdown Đón Năm Mới (+120 ngày)
            (24, 0, 500000, 800), (24, 1, 1000000, 300), (24, 2, 2000000, 80),

            # Quá khứ năm nay
            # Event 25: Bolero Xưa (-2 ngày)
            (25, 0, 180000, 10), (25, 1, 400000, 5), (25, 2, 750000, 2),
            # Event 26: Python Cơ Bản (-10 ngày)
            (26, 0, 150000, 8), (26, 1, 350000, 2),
            # Event 27: Futsal Doanh Nghiệp (-30 ngày)
            (27, 0, 80000, 50), (27, 1, 200000, 10),
            # Event 28: Ảnh Đương Đại (-60 ngày)
            (28, 0, 60000, 20), (28, 1, 150000, 5),
            # Event 29: AI Robotics (-90 ngày)
            (29, 0, 350000, 15), (29, 1, 800000, 4),
            # Event 30: Rock Sôi Động (-150 ngày)
            (30, 0, 200000, 30), (30, 1, 450000, 8),

            # Quá khứ 1 năm trước (year - 1)
            # Event 31: AI Spring
            (31, 0, 300000, 20), (31, 1, 750000, 5),
            # Event 32: Đêm Nhạc Hạ Vàng
            (32, 0, 280000, 40), (32, 1, 600000, 10), (32, 2, 1100000, 2),
            # Event 33: Bóng Đá Hè
            (33, 0, 100000, 80), (33, 1, 220000, 20),
            # Event 34: eSports Toàn Quốc
            (34, 0, 140000, 30), (34, 1, 320000, 10),

            # Quá khứ 2 năm trước (year - 2)
            # Event 35: Mùa Xuân Kỷ Niệm
            (35, 0, 250000, 30), (35, 1, 550000, 10), (35, 2, 1000000, 2),
            # Event 36: Bóng Đá Khởi Động
            (36, 0, 80000, 50), (36, 1, 180000, 15),
            # Event 37: Tech Expo Đột Phá
            (37, 0, 50000, 20), (37, 1, 120000, 5),
            # Event 38: DevOps Summit Thường Niên
            (38, 0, 200000, 10), (38, 1, 450000, 2),
        ]

        event_tickets = []
        for (ev_idx, tt_idx, price, qty) in et_tickets_data:
            et = EventTicket(
                event_id=events[ev_idx].id,
                ticket_type_id=ticket_types[tt_idx].id,
                price=price,
                quantity=qty,
            )
            event_tickets.append(et)
        db.session.add_all(event_tickets)
        db.session.flush()

        # Helper mapping: (event_index, ticket_type_index) -> EventTicket object
        et_map = {}
        for idx, (ev_idx, tt_idx, price, qty) in enumerate(et_tickets_data):
            et_map[(ev_idx, tt_idx)] = event_tickets[idx]

        # ===================== 8. VOUCHERS =====================
        # Cung cấp voucher còn hạn (tương lai), voucher hết hạn (quá khứ), và voucher hết số lượng
        vouchers = [
            # Voucher còn hạn (cho các sự kiện tương lai)
            Voucher(code="POPROCK10", discount_percentage=10,
                    expiration_date=rel_days(30), quantity=50, event_id=events[0].id),
            Voucher(code="EDM25", discount_percentage=25,
                    expiration_date=rel_days(30), quantity=30, event_id=events[1].id),
            Voucher(code="BONGDA15", discount_percentage=15,
                    expiration_date=rel_days(30), quantity=100, event_id=events[2].id),
            Voucher(code="AI2026", discount_percentage=15,
                    expiration_date=rel_days(30), quantity=40, event_id=events[7].id),
            Voucher(code="DIGITAL20", discount_percentage=20,
                    expiration_date=rel_days(30), quantity=50, event_id=events[8].id),
            Voucher(code="ESPORTS10", discount_percentage=10,
                    expiration_date=rel_days(30), quantity=80, event_id=events[14].id),
            Voucher(code="TECHFAIR20", discount_percentage=20,
                    expiration_date=rel_days(30), quantity=60, event_id=events[16].id),
            Voucher(code="VIPPRO50", discount_percentage=50,
                    expiration_date=rel_days(60), quantity=20, event_id=events[0].id),

            # Voucher ĐÃ HẾT HẠN (test không xuất hiện trong dropdown đặt vé)
            Voucher(code="EXPIRED10", discount_percentage=10,
                    expiration_date=rel_days(-5), quantity=50, event_id=events[0].id),

            # Voucher ĐÃ HẾT LƯỢT (quantity = 0, test không dùng được)
            Voucher(code="SOLDOUT20", discount_percentage=20,
                    expiration_date=rel_days(30), quantity=0, event_id=events[7].id),
        ]
        db.session.add_all(vouchers)
        db.session.flush()

        # ===================== 9. ORDERS =====================
        # (user_idx, order_date, items, voucher_idx_or_None, pm_idx, status, auth_code, face_url)
        # items = [((event_idx, ticket_type_idx), quantity), ...]

        face_portrait_1 = "https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg"
        face_portrait_2 = "https://res.cloudinary.com/dpxsbyyey/image/upload/v1775650754/avatar_user_nzinrm.webp"

        orders_data = [
            # -------------------------------------------------------------------------------------
            # A. ĐƠN HÀNG HÔM NAY (Đảm bảo Dashboard hiển thị số liệu ngay khi mở bộ lọc mặc định)
            # -------------------------------------------------------------------------------------
            # Order 0: Org 1 - Event 0 (Pop-Rock). Trạng thái PAID.
            # Đặt cách đây 1 giờ. cancellation limit = 24h. Sự kiện sau 3 ngày -> TEST HỦY VÉ THÀNH CÔNG!
            # Có mã QR và ảnh chân dung thật -> TEST SOÁT VÉ QR & FACE CHO ORG 1!
            (5, base_now - timedelta(hours=1),
             [((0, 0), 2), ((0, 1), 1)],
             0, 0, OrderStatus.PAID, "ET-ORG1-PAID-01", face_portrait_1),

            # Order 1: Org 2 - Event 7 (Workshop AI). Trạng thái PAID.
            # Đặt cách đây 2 giờ. Test Soát vé QR & Face cho Org 2!
            (6, base_now - timedelta(hours=2),
             [((7, 0), 1), ((7, 1), 1)],
             3, 1, OrderStatus.PAID, "ET-ORG2-PAID-02", face_portrait_2),

            # Order 2: Org 3 - Event 14 (eSports). Trạng thái PAID.
            # Đặt cách đây 3 giờ. Test Soát vé QR & Face cho Org 3!
            (7, base_now - timedelta(hours=3),
             [((14, 0), 2), ((14, 1), 1)],
             5, 2, OrderStatus.PAID, "ET-ORG3-PAID-03", face_portrait_1),

            # Order 3: Đơn hàng COMPLETED hôm nay -> test biểu đồ doanh thu ngày hôm nay
            (8, base_now - timedelta(hours=4),
             [((0, 0), 1)],
             None, 0, OrderStatus.COMPLETED, "ET-TODAY-COMP-04", face_portrait_2),

            # -------------------------------------------------------------------------------------
            # B. ĐƠN HÀNG TEST HỦY VÉ THẤT BẠI (QUÁ HẠN HỦY)
            # -------------------------------------------------------------------------------------
            # Order 4: Event 2 (Bóng Đá Cúp TP, Org 1, cancellation limit = 24h).
            # Đặt cách đây 3 ngày -> Quá hạn hủy (can_cancel_order == False) -> Nút hủy bị từ chối
            (5, base_now - timedelta(days=3),
             [((2, 0), 2)],
             2, 1, OrderStatus.PAID, "ET-EXPIRED-CANCEL-05", face_portrait_1),

            # -------------------------------------------------------------------------------------
            # C. ĐƠN HÀNG TUẦN NÀY & THÁNG NÀY (Test lọc theo Tuần và Tháng)
            # -------------------------------------------------------------------------------------
            # Order 5: Event 1 (EDM, Org 1) - COMPLETED, 2 ngày trước
            (6, base_now - timedelta(days=2),
             [((1, 0), 2), ((1, 1), 1)],
             1, 2, OrderStatus.COMPLETED, "ET-WEEK-06", face_portrait_2),

            # Order 6: Event 8 (Digital Transformation, Org 2) - COMPLETED, 3 ngày trước
            (7, base_now - timedelta(days=3),
             [((8, 0), 2)],
             4, 0, OrderStatus.COMPLETED, "ET-WEEK-07", face_portrait_1),

            # Order 7: Event 16 (Hội Chợ Tiêu Dùng, Org 3) - COMPLETED, 4 ngày trước
            (8, base_now - timedelta(days=4),
             [((16, 0), 4), ((16, 1), 1)],
             6, 1, OrderStatus.COMPLETED, "ET-WEEK-08", face_portrait_2),

            # Order 8: Event 4 (Marathon, Org 1) - COMPLETED (bán 85 vé -> còn 15% -> không gợi ý)
            (9, base_now - timedelta(days=5),
             [((4, 0), 85)],
             None, 2, OrderStatus.COMPLETED, "ET-MARATHON-09", face_portrait_1),

            # Order 9: Event 11 (Cybersecurity, Org 2) - COMPLETED (bán 90 vé -> còn 10% -> không gợi ý)
            (10, base_now - timedelta(days=6),
             [((11, 0), 90), ((11, 1), 27)],
             None, 0, OrderStatus.COMPLETED, "ET-CYBER-10", face_portrait_2),

            # Order 10: Event 18 (Mobile Gaming Pro, Org 3) - COMPLETED (bán 88 vé -> còn 12% -> không gợi ý)
            (11, base_now - timedelta(days=6),
             [((18, 0), 88), ((18, 1), 35)],
             None, 1, OrderStatus.COMPLETED, "ET-MOBIL-11", face_portrait_1),

            # Order 11: PENDING - Đang chờ thanh toán
            (5, base_now - timedelta(hours=5),
             [((2, 0), 1)],
             None, 0, OrderStatus.PENDING, "ET-PENDING-12", face_portrait_2),

            # Order 12: CANCELLED - Đã hủy
            (6, base_now - timedelta(days=1),
             [((0, 2), 1)],
             None, 1, OrderStatus.CANCELLED, "ET-CANCELLED-13", face_portrait_1),

            # -------------------------------------------------------------------------------------
            # D. ĐƠN HÀNG CÁC THÁNG TRƯỚC VÀ CÁC QUÝ TRONG NĂM NAY
            # -------------------------------------------------------------------------------------
            # Order 13: Event 25 (Bolero Xưa, -2 ngày trước) - COMPLETED
            (7, base_now - timedelta(days=5),
             [((25, 0), 3), ((25, 1), 1)],
             None, 0, OrderStatus.COMPLETED, "ET-PAST-14", face_portrait_2),

            # Order 14: Event 26 (Python Cơ Bản, -10 ngày trước) - COMPLETED
            (8, base_now - timedelta(days=15),
             [((26, 0), 2), ((26, 1), 1)],
             None, 2, OrderStatus.COMPLETED, "ET-PAST-15", face_portrait_1),

            # Order 15: Event 27 (Futsal Doanh Nghiệp, -30 ngày trước) - COMPLETED
            (9, base_now - timedelta(days=35),
             [((27, 0), 3)],
             None, 1, OrderStatus.COMPLETED, "ET-PAST-16", face_portrait_2),

            # Order 16: Event 28 (Ảnh Đương Đại, -60 ngày trước) - COMPLETED
            (10, base_now - timedelta(days=65),
             [((28, 0), 2), ((28, 1), 1)],
             None, 0, OrderStatus.COMPLETED, "ET-PAST-17", face_portrait_1),

            # Order 17: Event 29 (AI Robotics, -90 ngày trước, Quý trước) - COMPLETED
            (11, base_now - timedelta(days=95),
             [((29, 0), 2), ((29, 1), 1)],
             None, 2, OrderStatus.COMPLETED, "ET-PAST-18", face_portrait_2),

            # Order 18: Event 30 (Rock Sôi Động, -150 ngày trước) - COMPLETED
            (5, base_now - timedelta(days=155),
             [((30, 0), 4), ((30, 1), 1)],
             None, 1, OrderStatus.COMPLETED, "ET-PAST-19", face_portrait_1),

            # -------------------------------------------------------------------------------------
            # E. ĐƠN HÀNG 1 NĂM TRƯỚC (base_now.year - 1)
            # -------------------------------------------------------------------------------------
            # Order 19: Event 31 (AI Spring 2025)
            (6, rel_years(-1, 3, 1, 10, 0),
             [((31, 0), 2), ((31, 1), 1)],
             None, 0, OrderStatus.COMPLETED, "ET-Y1-20", face_portrait_2),

            # Order 20: Event 32 (Đêm Nhạc Hạ Vàng)
            (7, rel_years(-1, 5, 5, 14, 30),
             [((32, 0), 2), ((32, 1), 1)],
             None, 2, OrderStatus.COMPLETED, "ET-Y1-21", face_portrait_1),

            # Order 21: Event 33 (Bóng Đá Hè)
            (8, rel_years(-1, 8, 1, 9, 15),
             [((33, 0), 3)],
             None, 1, OrderStatus.COMPLETED, "ET-Y1-22", face_portrait_2),

            # Order 22: Event 34 (eSports Toàn Quốc)
            (9, rel_years(-1, 11, 10, 16, 45),
             [((34, 0), 2), ((34, 1), 1)],
             None, 0, OrderStatus.COMPLETED, "ET-Y1-23", face_portrait_1),

            # Order 23: Event 32 - Đã hủy năm ngoái
            (10, rel_years(-1, 5, 10, 11, 20),
             [((32, 2), 1)],
             None, 1, OrderStatus.CANCELLED, "ET-Y1-24", face_portrait_2),

            # -------------------------------------------------------------------------------------
            # F. ĐƠN HÀNG 2 NĂM TRƯỚC (base_now.year - 2)
            # -------------------------------------------------------------------------------------
            # Order 24: Event 35 (Mùa Xuân Kỷ Niệm 2024)
            (5, rel_years(-2, 1, 20, 10, 30),
             [((35, 0), 2), ((35, 1), 1)],
             None, 0, OrderStatus.COMPLETED, "ET-Y2-25", face_portrait_1),

            # Order 25: Event 36 (Bóng Đá Khởi Động 2024)
            (6, rel_years(-2, 3, 25, 14, 0),
             [((36, 0), 3)],
             None, 1, OrderStatus.COMPLETED, "ET-Y2-26", face_portrait_2),

            # Order 26: Event 37 (Tech Expo 2024)
            (7, rel_years(-2, 7, 1, 9, 0),
             [((37, 0), 2), ((37, 1), 1)],
             None, 2, OrderStatus.COMPLETED, "ET-Y2-27", face_portrait_1),

            # Order 27: Event 38 (DevOps Summit 2024)
            (8, rel_years(-2, 10, 5, 16, 30),
             [((38, 0), 1), ((38, 1), 1)],
             None, 0, OrderStatus.COMPLETED, "ET-Y2-28", face_portrait_2),
        ]

        orders = []
        for (user_idx, order_date, items, voucher_idx, pm_idx, order_status, auth_code, face_url) in orders_data:
            total = 0.0
            for (et_key, qty) in items:
                et = et_map[et_key]
                total += et.price * qty

            voucher_id = None
            if voucher_idx is not None:
                v = vouchers[voucher_idx]
                voucher_id = v.id
                discount = total * v.discount_percentage / 100
                total -= discount

            order = Order(
                user_id=users[user_idx].id,
                authentication_code=auth_code,
                authentication_face=face_url,
                status=order_status,
                total_price=max(0.0, total),
                date=order_date,
                voucher_id=voucher_id,
                payment_method_id=payment_methods[pm_idx].id,
            )
            orders.append(order)

        db.session.add_all(orders)
        db.session.flush()

        # Create order items
        order_items = []
        for i, (user_idx, order_date, items, voucher_idx, pm_idx, order_status, auth_code, face_url) in enumerate(orders_data):
            for (et_key, qty) in items:
                et = et_map[et_key]
                oi = OrderItem(
                    order_id=orders[i].id,
                    event_ticket_id=et.id,
                    quantity=qty,
                )
                order_items.append(oi)

        db.session.add_all(order_items)
        db.session.flush()

        # ===================== 10. EVENT REPORTS =====================
        reports = [
            EventReport(
                reporter_id=users[5].id,  # Hoàng Thị Vy
                event_id=events[25].id,   # Đêm Nhạc Bolero Xưa
                description="Âm thanh quá tệ, không nghe rõ bài hát. Loa bị rè nhiều lần.",
                date=rel_days(-1, 10, 0),
            ),
            EventReport(
                reporter_id=users[7].id,  # Phương Anh
                event_id=events[26].id,   # Workshop Python Cơ Bản
                description="Nội dung không đúng cam kết. Speaker chuẩn bị kém, tài liệu thiếu thốn.",
                date=rel_days(-9, 14, 30),
            ),
            EventReport(
                reporter_id=users[9].id,  # Minh Châu
                event_id=events[28].id,   # Triển Lãm Ảnh Đương Đại
                description="Hình ảnh quảng cáo khác xa thực tế. Số lượng tranh trưng bày rất ít.",
                date=rel_days(-58, 9, 0),
            ),
            EventReport(
                reporter_id=users[6].id,  # Thanh Sơn
                event_id=events[7].id,    # Workshop Generative AI 2026 (Sự kiện tương lai)
                description="Thông tin phòng hội thảo trên vé chưa rõ ràng. Cần gửi email hướng dẫn cụ thể.",
                date=base_now - timedelta(hours=3),
            ),
        ]
        db.session.add_all(reports)
        db.session.commit()

        print("=========================================================")
        print(" EzTicket Sample Data Created Successfully!")
        print("=========================================================")
        print(f"  - Base Time Anchor: {base_now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  - Event Types:      {len(event_types)}")
        print(f"  - Ticket Types:     {len(ticket_types)}")
        print(f"  - Payment Methods:  {len(payment_methods)}")
        print(f"  - Users:            {len(users)} (1 Admin, 3 Org Active, 1 Org Inactive, 8 Cus Active, 1 Cus Inactive)")
        print(f"  - Customer Profiles:{len(profiles)}")
        print(f"  - Events:           {len(events)} (Trải dài từ {base_now.year - 2} đến tương lai {base_now.year})")
        print(f"  - Event Tickets:    {len(event_tickets)}")
        print(f"  - Vouchers:         {len(vouchers)} (Còn hạn, hết hạn, hết lượt)")
        print(f"  - Orders:           {len(orders)} (PAID hôm nay, COMPLETED, PENDING, CANCELLED, các năm)")
        print(f"  - Order Items:      {len(order_items)}")
        print(f"  - Event Reports:    {len(reports)}")
        print("=========================================================")


if __name__ == "__main__":
    create_sample_data()
