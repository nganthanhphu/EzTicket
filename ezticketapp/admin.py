import hashlib
import math
from datetime import datetime
from flask import redirect, request, url_for, flash
from flask_login import current_user, logout_user
from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup

from ezticketapp import dao, db
from ezticketapp.models import Role, User, Event


class MyAdminIndex(AdminIndexView):
    base_template = 'admin/admin_base.html'

    @expose('/')
    def index(self):
        filter_type = request.args.get("filter_type", "").strip()
        date_val = request.args.get("date_val", "").strip()
        week_date = request.args.get("week_date", "").strip()
        year = request.args.get("year", type=int)
        quarter = request.args.get("quarter", type=int)
        month = request.args.get("month", type=int)
    # loc mac dịnh la theo ngay hien tai
        if not filter_type and not any([week_date, year, quarter, month]):
            filter_type = "date"
            if not date_val:
                date_val = datetime.now().strftime("%Y-%m-%d")
        elif filter_type == "date" and not date_val:
            date_val = datetime.now().strftime("%Y-%m-%d")

        events = dao.get_all_events()

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

        page = request.args.get("page", 1, type=int)
        per_page = 10

        total_items = len(events)
        total_pages = math.ceil(
            total_items / per_page) if total_items > 0 else 1
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages

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

        all_event_labels, all_event_revenues = dao.get_all_events_revenue(
            filter_type=filter_type,
            date_val=date_val,
            week_date=week_date,
            month=month,
            quarter=quarter,
            year=year
        )

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


class AdminView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == Role.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("admin_login", next=request.url))


class EventView(AdminView):
    can_create = False
    can_edit = False
    can_delete = True
    page_size = 10

    list_template = 'admin/events.html'

    @expose('/')
    def index(self):
        keyword = (request.args.get("keyword") or "").strip()
        page = request.args.get("page", 1, type=int)
        per_page = 10

        all_events = dao.get_all_events()
        if keyword:
            all_events = [
                e for e in all_events
                if keyword.lower() in e.name.lower()
                or keyword.lower() in e.location.lower()
                or (e.organizer and keyword.lower() in e.organizer.full_name.lower())
            ]

        total_items = len(all_events)
        total_pages = math.ceil(
            total_items / per_page) if total_items > 0 else 1
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages

        start = (page - 1) * per_page
        end = start + per_page
        paged_events = all_events[start:end]

        report_counts = dao.get_event_reports_stats()
        reports_grouped = dao.get_all_reports_grouped_by_event()

        return self.render(
            'admin/events.html',
            events=paged_events,
            keyword=keyword,
            page=page,
            total_pages=total_pages,
            total_items=total_items,
            report_counts=report_counts,
            reports_grouped=reports_grouped
        )

    @expose('/detail/<int:event_id>')
    def event_detail(self, event_id):
        event = dao.get_event_by_id(event_id)
        if not event:
            flash("Không tìm thấy sự kiện.")
            return redirect(url_for('event.index_view'))
        tickets = dao.load_event_tickets(event.id)
        vouchers = dao.load_event_vouchers(event.id)
        reports = dao.get_event_reports(event.id)
        return self.render('admin/event_detail.html', event=event, tickets=tickets, vouchers=vouchers, reports=reports)

    @expose('/toggle-active/<int:event_id>', methods=['POST'])
    def toggle_active(self, event_id):
        success, message = dao.toggle_event_active(event_id)
        flash(message)
        return redirect(request.referrer or url_for('event.index_view'))

    @expose('/delete-event/<int:event_id>')
    def delete_event(self, event_id):
        success, message = dao.delete_event(event_id)
        flash(message)
        return redirect(url_for('event.index_view'))


class LogoutView(BaseView):
    @expose('/')
    def index(self):
        logout_user()
        return redirect(url_for('admin_login'))

    def is_accessible(self) -> bool:
        return current_user.is_authenticated and current_user.role == Role.ADMIN


def init_admin(app):
    admin = Admin(
        app,
        name='EzTicket Admin',
        index_view=MyAdminIndex(name='Báo Cáo Doanh Thu', url='/admin')
    )

    admin.add_view(EventView(Event, db.session,
                   name="Quản lý sự kiện", endpoint="event"))
    admin.add_view(LogoutView(name="Đăng xuất"))

    return admin
