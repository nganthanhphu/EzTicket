import hashlib
from flask import redirect, request, url_for
from flask_login import current_user
from flask_admin import Admin, AdminIndexView, expose

from ezticketapp import dao, db
from ezticketapp.models import Role, User



class RevenueStatsView(AdminIndexView):
    base_template = 'admin/admin_base.html'

    @expose('/')
    def index(self):
        year = request.args.get("year", type=int)
        quarter = request.args.get("quarter", type=int)
        month = request.args.get("month", type=int)

        events = dao.get_all_events()

        # Top 5 sự kiện có doanh thu cao nhất
        top_5_events = dao.get_admin_top_revenue_events(
            limit=5,
            month=month,
            quarter=quarter,
            year=year
        )

        labels = [item['event'].name for item in top_5_events]
        revenues = [item['revenue'] for item in top_5_events]

        # Phân trang bảng chi tiết doanh thu (10 sự kiện mỗi trang)
        page = request.args.get("page", 1, type=int)
        per_page = 10
    
        import math
        total_items = len(events)
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages

        # Tính tổng doanh thu toàn hệ thống 
        total_revenue = sum(
            float(dao.revenue_event(e.id, month=month, quarter=quarter, year=year) or 0)
            for e in events
        )

        # Lấy danh sách sự kiện phân trang
        start = (page - 1) * per_page
        end = start + per_page
        paged_events = events[start:end]

        all_event_stats = []
        for e in paged_events:
            rev = float(
                dao.revenue_event(
                    e.id,
                    month=month,
                    quarter=quarter,
                    year=year
                ) or 0
            )

            all_event_stats.append({
                'event': e,
                'revenue': rev
            })

        years = dao.get_revenue_years()

        return self.render(
            'admin/dashboard.html',
            total_events=len(events),
            labels=labels,
            revenues=revenues,
            selected_year=year,
            selected_quarter=quarter,
            selected_month=month,
            total_revenue=total_revenue,
            years=years,
            all_event_stats=all_event_stats,
            page=page,
            total_pages=total_pages,
            start_stt=start + 1
        )

    def is_accessible(self):
        return (
            current_user.is_authenticated
            and current_user.role == Role.ADMIN
        )

    def inaccessible_callback(self, name, **kwargs):
        return redirect(
            url_for('login', next=request.url)
        )

# tạo tài khoản admin nhanh => này sài chat GPT
def ensure_admin_user(app):
    with app.app_context():
        try:
            admin_user = User.query.filter_by(role=Role.ADMIN).first()
            pwd_hash = hashlib.md5("123456".encode("utf-8")).hexdigest()

            if not admin_user:
                admin_user = User(
                    full_name="Quản Trị Viên (Admin)",
                    email="admin@example.com",
                    password=pwd_hash,
                    role=Role.ADMIN,
                    active=True
                )
                db.session.add(admin_user)
                db.session.commit()
                print("=> Đã khởi tạo tài khoản Admin: admin@example.com / 123456")
            else:
                admin_user.password = pwd_hash
                admin_user.active = True
                db.session.commit()
                print("=> Tài khoản Admin sẵn sàng: admin@example.com / 123456")
        except Exception as e:
            print("Lỗi khởi tạo tài khoản Admin:", e)



def init_admin(app):
    ensure_admin_user(app)

    admin = Admin(
        app,
        name='EzTicket Admin',
        index_view=RevenueStatsView(
            name='Báo Cáo Doanh Thu',
            url='/admin'
        )
    )

    return admin