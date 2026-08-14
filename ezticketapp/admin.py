import hashlib
from datetime import datetime
from flask import redirect, request, url_for
from flask_login import current_user
from flask_admin import Admin, AdminIndexView, expose

from ezticketapp import dao, db
from ezticketapp.models import Role, User



class RevenueStatsView(AdminIndexView):
    base_template = 'admin/admin_base.html'

    @expose('/')
    def index(self):
        filter_type = request.args.get("filter_type", "").strip()
        date_val = request.args.get("date_val", "").strip()
        week_date = request.args.get("week_date", "").strip()
        year = request.args.get("year", type=int)
        quarter = request.args.get("quarter", type=int)
        month = request.args.get("month", type=int)
    #loc mac dịnh la theo ngay hien tai
        if not filter_type and not any([week_date, year, quarter, month]):
            filter_type = "date"
            if not date_val:
                date_val = datetime.now().strftime("%Y-%m-%d")
        elif filter_type == "date" and not date_val:
            date_val = datetime.now().strftime("%Y-%m-%d")

        events = dao.get_all_events()

        # Top 5 sự kiện có doanh thu cao nhất
        top_5_events = dao.get_admin_top_revenue_events(
            limit=5,
            filter_type=filter_type,
            date_val=date_val,
            week_date=week_date,
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
            float(
                dao.revenue_event(
                    e.id,
                    filter_type=filter_type,
                    date_val=date_val,
                    week_date=week_date,
                    month=month,
                    quarter=quarter,
                    year=year
                ) or 0
            )
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
                    filter_type=filter_type,
                    date_val=date_val,
                    week_date=week_date,
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

        # Thống kê doanh thu tất cả sự kiện (Line Chart)
        all_event_labels, all_event_revenues = dao.get_all_events_revenue(
            filter_type=filter_type,
            date_val=date_val,
            week_date=week_date,
            month=month,
            quarter=quarter,
            year=year
        )

        # Thống kê doanh thu theo ngày (Line Chart)
        daily_labels, daily_revenues = dao.get_daily_revenue_stats(
            filter_type=filter_type,
            date_val=date_val,
            week_date=week_date,
            month=month,
            quarter=quarter,
            year=year
        )

        return self.render(
            'admin/dashboard.html',
            total_events=len(events),
            labels=labels,
            revenues=revenues,
            all_event_labels=all_event_labels,
            all_event_revenues=all_event_revenues,
            daily_labels=daily_labels,
            daily_revenues=daily_revenues,
            selected_filter_type=filter_type,
            selected_date_val=date_val,
            selected_week_date=week_date,
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
        return redirect(url_for('admin_login', next=request.url))




def init_admin(app):


    admin = Admin(
        app,
        name='EzTicket Admin',
        index_view=RevenueStatsView(
            name='Báo Cáo Doanh Thu',
            url='/admin'
        )
    )

    return admin