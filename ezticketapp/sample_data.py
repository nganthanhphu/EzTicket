import hashlib
from datetime import datetime

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

        # ===================== EVENT TYPE =====================
        event_types = [
            EventType(name="Bóng đá"),
            EventType(name="Điện tử"),
            EventType(name="Hội thảo"),
            EventType(name="Âm nhạc"),
            EventType(name="Công nghệ"),
        ]
        db.session.add_all(event_types)
        db.session.flush()

        # ===================== TICKET TYPE =====================
        ticket_types = [
            TicketType(name="Thường"),
            TicketType(name="VIP"),
            TicketType(name="VIP Pro"),
        ]
        db.session.add_all(ticket_types)
        db.session.flush()

        # ===================== PAYMENT METHOD =====================
        payment_methods = [
            PaymentMethod(name="MoMo"),
            PaymentMethod(name="ZaloPay"),
            PaymentMethod(name="VNPay"),
        ]
        db.session.add_all(payment_methods)
        db.session.flush()

        # ===================== USERS =====================
        users = [
            User(full_name="Admin EzTicket", email="admin@example.com",
                 password=PWD_HASH, role=Role.ADMIN,
                 avatar="https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg"),
            User(full_name="Nguyễn Văn An", email="nguyenvan@ezticket.com",
                 password=PWD_HASH, role=Role.ORGANIZER,
                 avatar="https://res.cloudinary.com/dpxsbyyey/image/upload/v1775650754/avatar_user_nzinrm.webp"),
            User(full_name="Trần Thị Bình", email="tranthib@ezticket.com",
                 password=PWD_HASH, role=Role.ORGANIZER,
                 avatar="https://res.cloudinary.com/dpxsbyyey/image/upload/v1775650754/avatar_user_nzinrm.webp"),
            User(full_name="Lê Minh Chí", email="leminh@ezticket.com",
                 password=PWD_HASH, role=Role.ORGANIZER,
                 avatar="https://res.cloudinary.com/dpxsbyyey/image/upload/v1775650754/avatar_user_nzinrm.webp"),
            User(full_name="Hoàng Thị Vy", email="hoangvy@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER,
                 avatar="https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg"),
            User(full_name="Thanh Sơn", email="thanhson@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER,
                 avatar="https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg"),
            User(full_name="Phương Anh", email="phuonganh@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER,
                 avatar="https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg"),
            User(full_name="Đức Trung", email="ductrung@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER,
                 avatar="https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg"),
            User(full_name="Minh Châu", email="minhchau@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER,
                 avatar="https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg"),
            User(full_name="Quốc Đạt", email="quocdat@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER,
                 avatar="https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg"),
            User(full_name="Thùy My", email="thuymy@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER,
                 avatar="https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg"),
            User(full_name="Văn Hậu", email="vanhau@gmail.com",
                 password=PWD_HASH, role=Role.CUSTOMER,
                 avatar="https://res.cloudinary.com/dkzzyue98/image/upload/v1765023207/avatar_ipfsn6.jpg"),
        ]
        db.session.add_all(users)
        db.session.flush()

        # ===================== CUSTOMER PROFILES =====================
        profiles = [
            CustomerProfile(
                user_id=users[4].id, gender=Gender.FEMALE, preferred_event_type_id=event_types[3].id),
            CustomerProfile(
                user_id=users[5].id, gender=Gender.MALE, preferred_event_type_id=event_types[0].id),
            CustomerProfile(
                user_id=users[6].id, gender=Gender.FEMALE, preferred_event_type_id=event_types[2].id),
            CustomerProfile(
                user_id=users[7].id, gender=Gender.MALE, preferred_event_type_id=event_types[1].id),
            CustomerProfile(
                user_id=users[8].id, gender=Gender.FEMALE, preferred_event_type_id=event_types[4].id),
            CustomerProfile(
                user_id=users[9].id, gender=Gender.MALE, preferred_event_type_id=event_types[0].id),
            CustomerProfile(
                user_id=users[10].id, gender=Gender.FEMALE, preferred_event_type_id=event_types[3].id),
            CustomerProfile(
                user_id=users[11].id, gender=Gender.MALE, preferred_event_type_id=event_types[1].id),
        ]
        db.session.add_all(profiles)
        db.session.flush()

        # ===================== EVENTS =====================
        img = "https://images.unsplash.com/photo-"
        events_data = [
            # --- Tháng 8/2026 (8) ---
            ("Đêm nhạc Pop-Rock Việt", "Nhà thi đấu Phú Thọ, TP.HCM", img + "1501386761578-eac5c94b800a", 4, 24,
             datetime(2026, 8, 8, 19, 30), event_types[3].id, users[1].id),
            ("Workshop AI & Machine Learning", "SECC Quận 7, TP.HCM", img + "1485827404703-89b55fcc595e", 3, 12,
             datetime(2026, 8, 10, 8, 30), event_types[4].id, users[2].id),
            ("Giải Bóng đá Sinh viên", "Sân vận động Thống Nhất, TP.HCM", img + "1552674605-db6ffd4facb5", 5, 24,
             datetime(2026, 8, 12, 16, 0), event_types[0].id, users[1].id),
            ("Đêm nhạc EDM Festival", "Beach Bar Nha Trang", img + "1470225619355-5c5c2f0446eb", 5, 24,
             datetime(2026, 8, 15, 20, 0), event_types[3].id, users[1].id),
            ("Hội thảo Marketing Digital", "Pullman Hotel, TP.HCM", img + "1540575467063-178a50c2df87", 3, 24,
             datetime(2026, 8, 18, 8, 0), event_types[2].id, users[2].id),
            ("Triển lãm Tranh Nghệ thuật", "Bảo tàng Mỹ thuật TP.HCM", img + "1460661419201-fd4cecdf8a8b", 3, 12,
             datetime(2026, 8, 22, 10, 0), event_types[2].id, users[3].id),
            ("Workshop DevOps & Cloud", "ĐH FPT, Hà Nội", img + "1515879218367-8466d910aaa4", 3, 24,
             datetime(2026, 8, 25, 9, 0), event_types[4].id, users[2].id),
            ("Lễ hội Ẩm thực Việt Nam", "Công viên Gia Định, TP.HCM", img + "1555939594-58d7cb561ad1", 10, 48,
             datetime(2026, 8, 28, 9, 0), event_types[2].id, users[3].id),
            # --- Tháng 9/2026 (7) ---
            ("Liveshow Ca Nhạc Acoustic", "Phố đi bộ Nguyễn Huệ, TP.HCM", img + "1506157786151-b8491531f063", 4, 24,
             datetime(2026, 9, 2, 19, 0), event_types[3].id, users[1].id),
            ("Triển lãm Game & eSports", "Trung tâm Hội chợ TP.HCM", img + "1542751371-adc38448a05e", 6, 48,
             datetime(2026, 9, 5, 9, 0), event_types[1].id, users[3].id),
            ("Hội thảo Blockchain & Web3", "Khách sạn Rex, TP.HCM", img + "1519389359179-57921414cf25", 3, 24,
             datetime(2026, 9, 8, 8, 0), event_types[4].id, users[2].id),
            ("Giải Bóng đá Futsal", "Nhà thi đấu Quân khu 7, TP.HCM", img + "1431324155629-1a6deb1dec8d", 5, 24,
             datetime(2026, 9, 12, 18, 0), event_types[0].id, users[1].id),
            ("Workshop Cybersecurity", "ĐH Bách Khoa, TP.HCM", img + "1550751827-4bd374c3f58b", 3, 12,
             datetime(2026, 9, 15, 8, 30), event_types[4].id, users[2].id),
            ("Đêm nhạc Bolero", "Nhà hát Lớn Hà Nội", img + "1514320291840-2e0a9bf2a9ae", 4, 24,
             datetime(2026, 9, 18, 19, 30), event_types[3].id, users[1].id),
            ("Hội chợ Công nghệ TechFair", "SECC Quận 7, TP.HCM", img + "1475721027785-f74eccf877e2", 8, 48,
             datetime(2026, 9, 22, 9, 0), event_types[2].id, users[3].id),
            # --- Tháng 10/2026 (5) ---
            ("Giải eSports Valorant", "Nhà thi đấu Tân Bình, TP.HCM", img + "1542751371-adc38448a05e", 6, 48,
             datetime(2026, 10, 1, 13, 0), event_types[1].id, users[3].id),
            ("Marathon TP.HCM City Run", "Quận 1, TP.HCM", img + "1552674605-db6ffd4facb5", 1, 48,
             datetime(2026, 10, 5, 5, 30), event_types[0].id, users[1].id),
            ("Workshop Mobile App Development", "ĐH FPT, TP.HCM", img + "1512941831141-22350448b337", 3, 12,
             datetime(2026, 10, 8, 8, 30), event_types[4].id, users[2].id),
            ("Đêm nhạc Trữ Tình & Bolero", "Nhà hát Opera Hà Nội", img + "1514320291840-2e0a9bf2a9ae", 4, 24,
             datetime(2026, 10, 12, 19, 30), event_types[3].id, users[1].id),
            ("Hội thảo Du học Quốc tế", "Grand Hotel, TP.HCM", img + "1540575467063-178a50c2df87", 3, 24,
             datetime(2026, 10, 15, 8, 0), event_types[2].id, users[2].id),
            # --- Tháng 11/2026 (6) ---
            ("Workshop UX/UI Design", "ĐH Mở TP.HCM", img + "1561070791-2526d30994b5", 3, 12,
             datetime(2026, 11, 1, 8, 30), event_types[4].id, users[2].id),
            ("Giải Bóng đá League", "Sân QK7, TP.HCM", img + "1431324155629-1a6deb1dec8d", 5, 24,
             datetime(2026, 11, 5, 16, 0), event_types[0].id, users[1].id),
            ("Đêm nhạc Soul & R&B", "Warehouse District, TP.HCM", img + "1493225457124-a3eb161ffa5f", 4, 24,
             datetime(2026, 11, 10, 20, 0), event_types[3].id, users[1].id),
            ("Triển lãm Nghệ thuật Số", "The Factory, TP.HCM", img + "1558618666-fcd25c85f7e7", 4, 24,
             datetime(2026, 11, 15, 10, 0), event_types[1].id, users[3].id),
            ("Hội thảo Startup & Innovation", "Lotte Hotel, Hà Nội", img + "1475721027785-f74eccf877e2", 3, 24,
             datetime(2026, 11, 20, 8, 0), event_types[2].id, users[2].id),
            ("Lễ Trao Giải Gaming Awards", "Nhà hát Lớn TP.HCM", img + "1542751371-adc38448a05e", 5, 48,
             datetime(2026, 11, 25, 19, 0), event_types[1].id, users[3].id),
            # --- Tháng 12/2026 (2) ---
            ("Giải eSports Liên Minh Huyền Thoại", "Nhà thi đấu Tân Bình, TP.HCM", img + "1542751371-adc38448a05e", 6, 48,
             datetime(2026, 12, 1, 13, 0), event_types[1].id, users[3].id),
            ("Đêm nhạc Countdown 2027", "Bến Thành Square, TP.HCM", img + "1493225457124-a3eb161ffa5f", 8, 48,
             datetime(2026, 12, 31, 20, 0), event_types[3].id, users[1].id),
            # --- Sự kiện đã qua 2026 (5 - phục vụ báo cáo) ---
            ("Đêm nhạc Rap Underground", "Clup MTV, TP.HCM", img + "1493225457124-a3eb161ffa5f", 4, 24,
             datetime(2026, 6, 15, 21, 0), event_types[3].id, users[1].id),
            ("Workshop Web Development", "TechHub, Hà Nội", img + "1515879218367-8466d910aaa4", 2, 12,
             datetime(2026, 5, 20, 9, 0), event_types[4].id, users[2].id),
            ("Triển lãm Ảnh Nghệ thuật", "Bảo tàng Mỹ thuật, Đà Nẵng", img + "1460661419201-fd4cecdf8a8b", 3, 12,
             datetime(2026, 7, 1, 10, 0), event_types[2].id, users[3].id),
            ("Giải Bóng đá Mini", "Sân Phú Thọ, TP.HCM", img + "1552674605-db6ffd4facb5", 5, 24,
             datetime(2026, 6, 10, 15, 0), event_types[0].id, users[1].id),
            ("Hội thảo AI Summit", "JW Marriott, Hà Nội", img + "1475721027785-f74eccf877e2", 3, 24,
             datetime(2026, 4, 15, 8, 0), event_types[4].id, users[2].id),
            # --- Edge cases (4) ---
            ("Workshop Lập trình Python", "ĐH Mở TP.HCM", img + "1515879218367-8466d910aaa4", 2, 12,
             datetime(2026, 7, 31, 8, 0), event_types[4].id, users[2].id),
            ("Acoustic Night", "Coffee House Bùi Viện, TP.HCM", img + "1506157786151-b8491531f063", 4, 24,
             datetime(2026, 8, 1, 19, 0), event_types[3].id, users[1].id),
            ("Workshop Data Science", "ĐH Bách Khoa, TP.HCM", img + "1551288046-da764c7d12be", 3, 12,
             datetime(2026, 8, 2, 9, 0), event_types[4].id, users[2].id),
            # --- Sự kiện quá khứ 2024-2025 (6 - phục vụ orders cũ) ---
            ("Đêm nhạc Xuân 2024", "Nhà thi đấu Phú Thọ, TP.HCM", img + "1501386761578-eac5c94b800a", 4, 24,
             datetime(2024, 2, 10, 19, 30), event_types[3].id, users[1].id),
            ("Workshop Python Cơ Bản", "TechHub, Hà Nội", img + "1515879218367-8466d910aaa4", 2, 12,
             datetime(2024, 3, 15, 9, 0), event_types[4].id, users[2].id),
            ("Triển lãm Nghệ thuật Đương đại", "Bảo tàng Mỹ thuật TP.HCM", img + "1460661419201-fd4cecdf8a8b", 3, 12,
             datetime(2024, 5, 20, 10, 0), event_types[2].id, users[3].id),
            ("Giải Bóng đá Mùa Xuân", "Sân Thống Nhất, TP.HCM", img + "1552674605-db6ffd4facb5", 5, 24,
             datetime(2024, 4, 10, 16, 0), event_types[0].id, users[1].id),
            ("AI Conference 2025", "SECC Quận 7, TP.HCM", img + "1485827404703-89b55fcc595e", 3, 24,
             datetime(2025, 3, 10, 8, 0), event_types[4].id, users[2].id),
            ("Đêm Nhạc Mùa Đông 2025", "Nhà hát Lớn Hà Nội", img + "1514320291840-2e0a9bf2a9ae", 4, 24,
             datetime(2025, 12, 20, 19, 30), event_types[3].id, users[1].id),
        ]

        events = []
        for (name, location, image, purchase_limit, cancel_h, time, etype_id, org_id) in events_data:
            e = Event(
                name=name, location=location, image=image,
                purchase_limit=purchase_limit, cancellation_time_limit_by_hours=cancel_h,
                time=time, event_type_id=etype_id, organizer_id=org_id,
            )
            events.append(e)
        db.session.add_all(events)
        db.session.flush()

        # ===================== EVENT TICKETS =====================
        # (event_index, ticket_type_index, price, quantity)
        et_tickets_data = [
            # 0: Đêm nhạc Pop-Rock Việt
            (0, 0, 350000, 500), (0, 1, 700000, 200), (0, 2, 1200000, 50),
            # 1: Workshop AI
            (1, 0, 200000, 150), (1, 1, 500000, 50),
            # 2: Giải Bóng đá SV
            (2, 0, 100000, 1000), (2, 1, 250000, 200),
            # 3: EDM Festival
            (3, 0, 400000, 600), (3, 1, 800000, 250), (3, 2, 1500000, 60),
            # 4: Hội thảo Marketing
            (4, 0, 150000, 200), (4, 1, 400000, 50),
            # 5: Triển lãm Tranh
            (5, 0, 80000, 300), (5, 1, 200000, 80),
            # 6: Workshop DevOps
            (6, 0, 250000, 120), (6, 1, 600000, 30),
            # 7: Lễ hội Ẩm thực
            (7, 0, 50000, 2000), (7, 1, 150000, 500),
            # 8: Liveshow Acoustic
            (8, 0, 200000, 300), (8, 1, 450000, 100), (8, 2, 800000, 30),
            # 9: Triển lãm Game
            (9, 0, 120000, 500), (9, 1, 300000, 150), (9, 2, 600000, 40),
            # 10: Hội thảo Blockchain
            (10, 0, 300000, 150), (10, 1, 700000, 40),
            # 11: Giải Futsal
            (11, 0, 80000, 800), (11, 1, 200000, 200),
            # 12: Workshop Cybersecurity
            (12, 0, 250000, 100), (12, 1, 550000, 30),
            # 13: Đêm nhạc Bolero
            (13, 0, 180000, 400), (13, 1, 400000, 120), (13, 2, 750000, 35),
            # 14: TechFair
            (14, 0, 60000, 1500), (14, 1, 200000, 400),
            # 15: eSports Valorant
            (15, 0, 150000, 400), (15, 1, 350000, 120), (15, 2, 700000, 30),
            # 16: Marathon
            (16, 0, 200000, 500),
            # 17: Workshop Mobile
            (17, 0, 200000, 130), (17, 1, 450000, 40),
            # 18: Đêm nhạc Trữ Tình
            (18, 0, 200000, 350), (18, 1, 450000, 100), (18, 2, 850000, 25),
            # 19: Hội thảo Du học
            (19, 0, 100000, 250), (19, 1, 300000, 60),
            # 20: Workshop UX/UI
            (20, 0, 180000, 120), (20, 1, 400000, 35),
            # 21: Giải League
            (21, 0, 100000, 700), (21, 1, 250000, 180),
            # 22: Soul & R&B
            (22, 0, 250000, 300), (22, 1, 550000, 100), (22, 2, 1000000, 25),
            # 23: Triển lãm Nghệ thuật Số
            (23, 0, 100000, 400), (23, 1, 250000, 100),
            # 24: Startup & Innovation
            (24, 0, 200000, 200), (24, 1, 500000, 50),
            # 25: Gaming Awards
            (25, 0, 150000, 500), (25, 1, 350000, 150), (25, 2, 700000, 40),
            # 26: eSports LMHT
            (26, 0, 150000, 500), (26, 1, 350000, 150), (26, 2, 700000, 40),
            # 27: Countdown 2027
            (27, 0, 500000, 800), (27, 1, 1000000, 300), (27, 2, 2000000, 80),
            # 28: Đêm nhạc Rap (past)
            (28, 0, 200000, 300), (28, 1, 450000, 80),
            # 29: Workshop Web Dev (past)
            (29, 0, 150000, 100), (29, 1, 350000, 30),
            # 30: Triển lãm Ảnh (past)
            (30, 0, 60000, 250), (30, 1, 150000, 60),
            # 31: Giải Mini (past)
            (31, 0, 70000, 600), (31, 1, 180000, 150),
            # 32: AI Summit (past)
            (32, 0, 400000, 200), (32, 1, 900000, 50),
            # 33: Workshop Python (edge - soon)
            (33, 0, 150000, 80), (33, 1, 350000, 20),
            # 34: Acoustic Night (edge - almost sold out)
            (34, 0, 180000, 2),
            # 35: Workshop Data Science (edge - sold out)
            (35, 0, 200000, 0), (35, 1, 450000, 0),
            # 36: Đêm nhạc Xuân 2024
            (36, 0, 250000, 400), (36, 1, 550000, 120), (36, 2, 1000000, 30),
            # 37: Workshop Python 2024
            (37, 0, 100000, 100), (37, 1, 250000, 30),
            # 38: Triển lãm 2024
            (38, 0, 50000, 200), (38, 1, 120000, 50),
            # 39: Giải Mùa Xuân 2024
            (39, 0, 80000, 800), (39, 1, 200000, 200),
            # 40: AI Conference 2025
            (40, 0, 350000, 250), (40, 1, 800000, 60),
            # 41: Đêm Nhạc Mùa Đông 2025
            (41, 0, 300000, 350), (41, 1, 650000, 100), (41, 2, 1200000, 25),
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

        # ===================== VOUCHERS =====================
        vouchers = [
            Voucher(code="POPROCK10", discount_percentage=10, expiration_date=datetime(2026, 8, 5),
                    quantity=50, event_id=events[0].id),
            Voucher(code="AI2026", discount_percentage=15, expiration_date=datetime(2026, 8, 8),
                    quantity=30, event_id=events[1].id),
            Voucher(code="BONGDA50", discount_percentage=5, expiration_date=datetime(2026, 8, 10),
                    quantity=100, event_id=events[2].id),
            Voucher(code="EDM2026", discount_percentage=20, expiration_date=datetime(2026, 8, 12),
                    quantity=20, event_id=events[3].id),
            Voucher(code="SUMMER25", discount_percentage=25, expiration_date=datetime(2026, 12, 31),
                    quantity=40, event_id=events[20].id),
            Voucher(code="TECHFAIR", discount_percentage=10, expiration_date=datetime(2026, 9, 20),
                    quantity=60, event_id=events[14].id),
        ]
        db.session.add_all(vouchers)
        db.session.flush()

        # ===================== ORDERS =====================
        # Helper: find event_ticket by (event_index, ticket_type_index)
        et_map = {}
        for idx, (ev_idx, tt_idx, price, qty) in enumerate(et_tickets_data):
            et_map[(ev_idx, tt_idx)] = event_tickets[idx]

        # Orders data: (user_index, date, items, voucher_index_or_None, payment_method_index, status)
        # items = [(event_ticket_key, quantity), ...]
        orders_data = [
            # ===== 2024 (6 orders) =====
            # Order 1 - user id5 (Hoàng Vy) - Đêm nhạc Xuân 2024
            (4, datetime(2024, 1, 20, 10, 30),
             [((36, 0), 2), ((36, 1), 1)],
             None, 0, OrderStatus.COMPLETED),
            # Order 2 - user id6 (Thanh Sơn) - Workshop Python 2024
            (5, datetime(2024, 2, 25, 14, 0),
             [((37, 0), 1)],
             None, 1, OrderStatus.COMPLETED),
            # Order 3 - user id7 (Phương Anh) - Triển lãm 2024
            (6, datetime(2024, 4, 10, 9, 15),
             [((38, 0), 2), ((38, 1), 1)],
             None, 2, OrderStatus.COMPLETED),
            # Order 4 - user id8 (Đức Trung) - Giải Bóng đá 2024
            (7, datetime(2024, 3, 5, 16, 45),
             [((39, 0), 3)],
             None, 0, OrderStatus.COMPLETED),
            # Order 5 - user id9 (Minh Châu) - Đêm nhạc Xuân 2024 - CANCELLED
            (8, datetime(2024, 1, 28, 11, 20),
             [((36, 2), 1)],
             None, 1, OrderStatus.CANCELLED),
            # Order 6 - user id5 (Hoàng Vy) - Workshop Python 2024
            (4, datetime(2024, 3, 1, 8, 0),
             [((37, 0), 1), ((37, 1), 1)],
             None, 2, OrderStatus.COMPLETED),
            # ===== 2025 (10 orders) =====
            # Order 7 - user id6 - AI Conference 2025
            (5, datetime(2025, 1, 15, 9, 30),
             [((40, 0), 2)],
             None, 0, OrderStatus.COMPLETED),
            # Order 8 - user id7 - AI Conference 2025
            (6, datetime(2025, 2, 1, 14, 0),
             [((40, 0), 1), ((40, 1), 1)],
             None, 2, OrderStatus.COMPLETED),
            # Order 9 - user id8 - Đêm Nhạc Mùa Đông 2025
            (7, datetime(2025, 10, 5, 10, 0),
             [((41, 0), 2)],
             None, 1, OrderStatus.COMPLETED),
            # Order 10 - user id9 - Đêm Nhạc Mùa Đông 2025
            (8, datetime(2025, 11, 10, 16, 30),
             [((41, 1), 1)],
             None, 0, OrderStatus.COMPLETED),
            # Order 11 - user id10 - AI Conference 2025 - CANCELLED
            (9, datetime(2025, 1, 20, 11, 0),
             [((40, 1), 2)],
             None, 2, OrderStatus.CANCELLED),
            # Order 12 - user id11 - Đêm Nhạc Mùa Đông 2025
            (10, datetime(2025, 11, 25, 13, 15),
             [((41, 0), 1), ((41, 2), 1)],
             None, 0, OrderStatus.COMPLETED),
            # Order 13 - user id12 - AI Conference 2025
            (11, datetime(2025, 2, 10, 8, 45),
             [((40, 0), 3)],
             None, 1, OrderStatus.COMPLETED),
            # Order 14 - user id5 - Đêm Nhạc Mùa Đông 2025
            (4, datetime(2025, 10, 20, 9, 0),
             [((41, 0), 1)],
             None, 2, OrderStatus.COMPLETED),
            # Order 15 - user id6 - AI Conference 2025
            (5, datetime(2025, 2, 28, 15, 30),
             [((40, 0), 1)],
             None, 0, OrderStatus.COMPLETED),
            # Order 16 - user id7 - Đêm Nhạc Mùa Đông 2025 - CANCELLED
            (6, datetime(2025, 12, 1, 10, 0),
             [((41, 0), 2), ((41, 1), 1)],
             None, 1, OrderStatus.CANCELLED),
            # ===== 2026 (14 orders - đến 07/30) =====
            # Order 17 - user id5 - Workshop AI (event 1) - COMPLETED, voucher
            (4, datetime(2026, 6, 25, 9, 0),
             [((1, 0), 1), ((1, 1), 1)],
             1, 0, OrderStatus.COMPLETED),
            # Order 18 - user id6 - Đêm nhạc Pop-Rock (event 0)
            (5, datetime(2026, 7, 1, 14, 30),
             [((0, 0), 2)],
             None, 2, OrderStatus.COMPLETED),
            # Order 19 - user id7 - Workshop DevOps (event 6)
            (6, datetime(2026, 7, 5, 10, 0),
             [((6, 0), 1)],
             None, 1, OrderStatus.COMPLETED),
            # Order 20 - user id8 - Liveshow Acoustic (event 8)
            (7, datetime(2026, 7, 10, 16, 0),
             [((8, 0), 2), ((8, 1), 1)],
             None, 0, OrderStatus.COMPLETED),
            # Order 21 - user id9 - Triển lãm Game (event 9) - COMPLETED, voucher
            (8, datetime(2026, 7, 15, 11, 30),
             [((9, 0), 3)],
             5, 2, OrderStatus.COMPLETED),
            # Order 22 - user id10 - Giải Bóng đá SV (event 2)
            (9, datetime(2026, 7, 18, 8, 0),
             [((2, 0), 2)],
             None, 0, OrderStatus.COMPLETED),
            # Order 23 - user id11 - Workshop Cybersecurity (event 12)
            (10, datetime(2026, 7, 20, 14, 0),
             [((12, 0), 1), ((12, 1), 1)],
             None, 1, OrderStatus.COMPLETED),
            # Order 24 - user id12 - EDM Festival (event 3) - COMPLETED, voucher
            (11, datetime(2026, 7, 22, 9, 30),
             [((3, 0), 2), ((3, 1), 1)],
             3, 2, OrderStatus.COMPLETED),
            # Order 25 - user id5 - Hội thảo Marketing (event 4) - PENDING
            (4, datetime(2026, 7, 25, 10, 0),
             [((4, 0), 1)],
             None, 0, OrderStatus.PENDING),
            # Order 26 - user id6 - Workshop Lập trình Python (event 33, edge) - PENDING
            (5, datetime(2026, 7, 28, 15, 0),
             [((33, 0), 1)],
             None, 1, OrderStatus.PENDING),
            # Order 27 - user id7 - Giải Bóng đá Futsal (event 11)
            (6, datetime(2026, 7, 10, 9, 0),
             [((11, 0), 2)],
             None, 2, OrderStatus.COMPLETED),
            # Order 28 - user id8 - Workshop UX/UI (event 20) - CANCELLED
            (7, datetime(2026, 7, 20, 11, 0),
             [((20, 0), 1), ((20, 1), 1)],
             None, 0, OrderStatus.CANCELLED),
            # Order 29 - user id9 - Đêm nhạc Bolero (event 13) - PENDING, voucher
            (8, datetime(2026, 7, 29, 8, 30),
             [((13, 0), 2)],
             0, 1, OrderStatus.PENDING),
            # Order 30 - user id10 - Acoustic Night (event 34, edge)
            (9, datetime(2026, 7, 26, 10, 0),
             [((34, 0), 2)],
             None, 2, OrderStatus.COMPLETED),
        ]

        orders = []
        order_items = []
        auth_counter = 100000

        for (user_idx, order_date, items, voucher_idx, pm_idx, order_status) in orders_data:
            auth_counter += 1
            total = 0.0
            for (et_key, qty) in items:
                et = et_map[et_key]
                total += et.price * qty

            discount = 0.0
            voucher_id = None
            if voucher_idx is not None:
                v = vouchers[voucher_idx]
                voucher_id = v.id
                discount = total * v.discount_percentage / 100
                total -= discount

            order = Order(
                user_id=users[user_idx].id,
                authentication_code=f"ET{auth_counter}",
                authentication_face=f"https://example.com/selfie/{auth_counter}.jpg",
                status=order_status,
                total_price=total,
                date=order_date,
                voucher_id=voucher_id,
                payment_method_id=payment_methods[pm_idx].id,
            )
            orders.append(order)

        db.session.add_all(orders)
        db.session.flush()

        # Create order items
        oi_counter = 0
        for i, (user_idx, order_date, items, voucher_idx, pm_idx, order_status) in enumerate(orders_data):
            for (et_key, qty) in items:
                et = et_map[et_key]
                oi = OrderItem(
                    order_id=orders[i].id,
                    event_ticket_id=et.id,
                    quantity=qty,
                )
                order_items.append(oi)
                oi_counter += 1

        db.session.add_all(order_items)
        db.session.flush()

        # ===================== EVENT REPORTS =====================
        reports = [
            EventReport(
                reporter_id=users[4].id,  # Hoàng Vy
                event_id=events[28].id,   # Đêm nhạc Rap Underground
                description="Am thanh qua te, khong nghe ro bai hat. Loa bi reo nhieu lan.",
                date=datetime(2026, 6, 16, 10, 0),
            ),
            EventReport(
                reporter_id=users[6].id,  # Phương Anh
                event_id=events[29].id,   # Workshop Web Development
                description="Noi dung khong dung cam ket. Speaker chuan bi kem, tai lieu thieu.",
                date=datetime(2026, 5, 21, 14, 30),
            ),
            EventReport(
                reporter_id=users[8].id,  # Minh Châu
                event_id=events[30].id,   # Triển lãm Ảnh
                description="Hinh anh quang cao khac xa thuc te. So luong buc anh rat it.",
                date=datetime(2026, 7, 2, 9, 0),
            ),
            EventReport(
                reporter_id=users[5].id,  # Thanh Sơn
                event_id=events[1].id,    # Workshop AI (tương lai)
                description="Thong tin dia diem khong ro rang. Ban do chi dan sai.",
                date=datetime(2026, 7, 28, 16, 0),
            ),
        ]
        db.session.add_all(reports)
        db.session.commit()

        print("Sample data created successfully!")
        print(f"  - {len(event_types)} event types")
        print(f"  - {len(ticket_types)} ticket types")
        print(f"  - {len(payment_methods)} payment methods")
        print(f"  - {len(users)} users")
        print(f"  - {len(profiles)} customer profiles")
        print(f"  - {len(events)} events")
        print(f"  - {len(event_tickets)} event tickets")
        print(f"  - {len(vouchers)} vouchers")
        print(f"  - {len(orders)} orders")
        print(f"  - {len(order_items)} order items")
        print(f"  - {len(reports)} event reports")


if __name__ == "__main__":
    create_sample_data()
