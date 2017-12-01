# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from datetime import timedelta, datetime
import collections
from operator import itemgetter
from calendar import monthrange
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


class holiday_master(osv.Model):

    _inherit = "holiday.master"

    _columns = {
        'color': fields.char('Color', default='green')
    }


class res_partner(osv.Model):
    _inherit = "res.partner"

    _columns = {
        'team_id': fields.many2one('user.team', 'Team')
    }


class user_team(osv.Model):
    _name = "user.team"
    _description = "User Team details"

    _columns = {
        'name': fields.char("Name"),
        'manager_id': fields.many2one('res.partner', 'Manager'),
        'user_ids': fields.many2many('res.partner', 'partner_team_rel',
                                'partner_id', 'team_id', 'Team Members')
    }


class calendar_event(osv.Model):
    _inherit = 'calendar.event'

    _columns = {
        'event_type': fields.selection([('meeting', 'Meeting'),
                                        ('reminder', 'Reminders'),
                                        ('anniversaries', 'Anniversaries')],
                                       "Entry Type"),
        'team_id': fields.many2one('user.team', 'Team'),
        'manager_id': fields.many2one('res.partner', 'Manager'),
        'not_workday': fields.selection([('dont_move', 'Don\'t Move'),
                                         ('nearest_day',
                                          'Move to nearest working day'),
                                         ('next_day', 'Next working day'),
                                         ('pre_day', 'Previous working day'),
                                         ('delete', 'Delete')],
                                'If a meeting doesn\'t fall on a work day'),
        'month_by': fields.selection([('date', 'Date of month'),
                                      ('day', 'Day of month'),
                                      ('last_day', 'Last Day of month')],
                                     'Option', oldname='select1'),
    }

    _defaults = {
        'event_type': 'reminder',
        'not_workday': 'pre_day'
     }

    def get_recurrent_ids(self, cr, uid, event_id, domain, order=None,
                          context=None):

        """Gives virtual event ids for recurring events
        This method gives ids of dates that comes between start date and
        end date of calendar views

        @param order: The fields (comma separated, format "FIELD {DESC|ASC}")
        on which the events should be sorted
        """
        if not context:
            context = {}

        if isinstance(event_id, (basestring, int, long)):
            ids_to_browse = [event_id]  # keep select for return
        else:
            ids_to_browse = event_id

        if order:
            order_fields = [field.split()[0] for field in order.split(',')]
        else:
            # fallback on self._order defined on the model
            order_fields = [field.split()[0]
                            for field in self._order.split(',')]

        if 'id' not in order_fields:
            order_fields.append('id')

        result_data = []
        result = []
        for ev in self.browse(cr, uid, ids_to_browse, context=context):
            if not ev.recurrency or not ev.rrule:
                result.append(ev.id)
                result_data.append(self.get_search_fields(ev, order_fields))
                continue
            rdates = self.get_recurrent_date_by_event(cr, uid, ev,
                                                      context=context)
            no_workday = ev.not_workday
            if no_workday == 'nearest_day':
                no_workday = 'pre_day'

            for r_date in rdates:
                if ev.month_by == 'last_day':
                    r_date_temp = r_date.strftime(
                                              '%Y-%m-%d %H:%M:%S').split("-")
                    year = int(r_date_temp[0])
                    day_list = {'01': 1, '02': 2, '03': 3, '04': 4,
                                '05': 5, '06': 6, '07': 7, '08': 8,
                                '09': 9, '10': 10, '11': 11, '12': 12}
                    month = day_list.get(str(r_date_temp[1]))
                    month_range = monthrange(year, month)[1]
                    new_date = (str(r_date_temp[0]) + '-' +
                                str(r_date_temp[1]) + '-' +
                                str(month_range) + ' ' +
                                r_date_temp[2].split(' ')[1])
                    r_date = r_date.strptime(new_date, '%Y-%m-%d %H:%M:%S')
                # check whether the date is on saturday or sunday
                if r_date.weekday() == 5:
                    if no_workday == 'next_day':
                        r_date = r_date + timedelta(days=2)
                    if no_workday == 'pre_day':
                        r_date = r_date - timedelta(days=1)
                    if no_workday == 'delete':
                        rdates.remove(r_date)
                if r_date.weekday() == 6:
                    if no_workday == 'next_day':
                        r_date = r_date + timedelta(days=1)
                    if no_workday == 'pre_day':
                        r_date = r_date - timedelta(days=2)
                    if no_workday == 'delete':
                        rdates.remove(r_date)
                # fix domain evaluation
                # step 1: check date and replace expression by True or False,
                #         replace other expressions by True
                # step 2: evaluation of & and |
                # check if there are one False
                pile = []
                ok = True
                for arg in domain:
                    if str(arg[0]) in ('start', 'stop', 'final_date'):
                        if (arg[1] == '='):
                            ok = r_date.strftime('%Y-%m-%d') == arg[2]
                        if (arg[1] == '>'):
                            ok = r_date.strftime('%Y-%m-%d') > arg[2]
                        if (arg[1] == '<'):
                            ok = r_date.strftime('%Y-%m-%d') < arg[2]
                        if (arg[1] == '>='):
                            ok = r_date.strftime('%Y-%m-%d') >= arg[2]
                        if (arg[1] == '<='):
                            ok = r_date.strftime('%Y-%m-%d') <= arg[2]
                        pile.append(ok)
                    elif str(arg) == str('&') or str(arg) == str('|'):
                        pile.append(arg)
                    else:
                        pile.append(True)
                pile.reverse()
                new_pile = []
                for item in pile:
                    if not isinstance(item, basestring):
                        res = item
                    elif str(item) == str('&'):
                        first = new_pile.pop()
                        second = new_pile.pop()
                        res = first and second
                    elif str(item) == str('|'):
                        first = new_pile.pop()
                        second = new_pile.pop()
                        res = first or second
                    new_pile.append(res)

                if [True for item in new_pile if not item]:
                    continue
                result_data.append(self.get_search_fields(ev, order_fields,
                                                          r_date=r_date))

        if order_fields:
            uniq = lambda it: collections.OrderedDict((id(x), x)
                                                      for x in it).values()

            def comparer(left, right):
                for fn, mult in comparers:
                    result = cmp(fn(left), fn(right))
                    if result:
                        return mult * result
                return 0

            sort_params = [key.split()[0] if key[-4:].lower() != 'desc' else '-%s' % key.split()[0] for key in (order or self._order).split(',')]
            sort_params = uniq([comp if comp not in ['start', 'start_date', 'start_datetime'] else 'sort_start' for comp in sort_params])
            sort_params = uniq([comp if comp not in ['-start', '-start_date', '-start_datetime'] else '-sort_start' for comp in sort_params])
            comparers = [((itemgetter(col[1:]), -1) if col[0] == '-' else (itemgetter(col), 1)) for col in sort_params]
            ids = [r['id'] for r in sorted(result_data, cmp=comparer)]

        if isinstance(event_id, (basestring, int, long)):
            return ids and ids[0] or False
        else:
            return ids

    def get_event_details(self, cr, uid, event_id, context=None):
        res = self.get_recurrent_ids(cr, uid, event_id, {})
        duration = 0.0
        user_name = False
        for event in self.browse(cr, uid, event_id, context=context):
            duration = event.duration
            if event.user_id:
                user_name = event.user_id.name
        return [res, {'duration': duration, 'user_name': user_name}]

    def team_id_change(self, cr, uid, ids, team_id, partner_ids, context=None):
        users = []
        if team_id:
            team_obj = self.pool.get('user.team')
            team_rec = team_obj.browse(cr, uid, team_id, context=context)
            users = [user.id for user in team_rec.user_ids]
            if partner_ids and not users:
                users = partner_ids[0][2]
            else:
                users = users + (partner_ids[0][2])
            if team_rec.manager_id:
                users.append(team_rec.manager_id.id)
            return {'value': {'manager_id': (team_rec.manager_id and
                                         team_rec.manager_id.id),
                          'partner_ids': [(6, 0, users)]}}
        if partner_ids:
            users = partner_ids[0][2]
        return {'value': {'partner_ids': [(6, 0, users)]}}

    def manager_id_change(self, cr, uid, ids, manager_id, partner_ids,
                          context=None):
        users = []
        if manager_id:
            if partner_ids:
                users = partner_ids[0][2]
            if manager_id not in users:
                users.append(manager_id)
        else:
            if partner_ids:
                users = partner_ids[0][2]
        return {'value': {'partner_ids': [(6, 0, users)]}}

    def onchange_dates(self, cr, uid, ids, fromtype, start=False, end=False,
                       checkallday=False, allday=False, context=None):

        """Returns duration and end date based on values passed
        @param ids: List of calendar event's IDs.
        """
        value = {}

        if checkallday != allday:
            return value

        value['allday'] = checkallday  # Force to be rewrited

        if allday:
            if fromtype == 'start' and start:
                if ids:
                    rec = self.browse(cr, uid, ids, context=context)
                    if not rec.day:
                        day_temp = start.split("-")[2]
                        value["day"] = day_temp
                else:
                    day_temp = start.split("-")[2]
                    value["day"] = day_temp
                start = datetime.strptime(start, DEFAULT_SERVER_DATE_FORMAT)
                value['start_datetime'] = datetime.strftime(start,
                                                DEFAULT_SERVER_DATETIME_FORMAT)
                value['start'] = datetime.strftime(start,
                                               DEFAULT_SERVER_DATETIME_FORMAT)

            if fromtype == 'stop' and end:
                end = datetime.strptime(end, DEFAULT_SERVER_DATE_FORMAT)
                value['stop_datetime'] = datetime.strftime(end,
                                               DEFAULT_SERVER_DATETIME_FORMAT)
                value['stop'] = datetime.strftime(end,
                                              DEFAULT_SERVER_DATETIME_FORMAT)

        else:
            if fromtype == 'start' and start:
                if ids:
                    rec = self.browse(cr, uid, ids, context=context)
                    if not rec.day:
                        day_temp = start.split(" ")[0].split("-")[2]
                        value["day"] = day_temp
                else:
                    day_temp = start.split(" ")[0].split("-")[2]
                    value["day"] = day_temp
                start = datetime.strptime(start,
                                          DEFAULT_SERVER_DATETIME_FORMAT)
                value['start_date'] = datetime.strftime(start,
                                                DEFAULT_SERVER_DATE_FORMAT)
                value['start'] = datetime.strftime(start,
                                               DEFAULT_SERVER_DATETIME_FORMAT)
            if fromtype == 'stop' and end:
                end = datetime.strptime(end,
                                        DEFAULT_SERVER_DATETIME_FORMAT)
                value['stop_date'] = datetime.strftime(end,
                                                   DEFAULT_SERVER_DATE_FORMAT)
                value['stop'] = datetime.strftime(end,
                                              DEFAULT_SERVER_DATETIME_FORMAT)

        return {'value': value}
