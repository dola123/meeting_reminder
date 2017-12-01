# -*- coding: utf-8 -*-

from openerp import fields, models
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


class notify_holiday(models.Model):
    _name = "notify.holiday"

    _columns = {
            'partner_id': fields.Many2one('res.partner', 'User'),
            'email': fields.Char('Email Sent to'),
            'holiday_id': fields.Many2one('holiday.master', 'Holiday')
    }


class holiday_master(models.Model):
    _name = 'holiday.master'

    _columns = {
            'name': fields.Char('Holiday Name', required=True),
            'section_id': fields.Many2one('crm.case.section', 'Sales Group',
                                          select=True,
                                          track_visibility='onchange',
                                          help='When sending mails,\
                                          the default email address is taken\
                                          from the sales team.'),
            'start_date': fields.date('Start Date'),
            'stop_date': fields.date('End Date'),
            'notified_users': fields.one2many('notify.holiday', 'holiday_id',
                                              'Notified User for the Holiday')
    }

    def _notify_holiday(self, cr, uid, ids=None, context=None):
        ''' This method adds the Abandoned Products if product is there in
            the Cart for 4 hours and sends mail to login customer.
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : list of holiday master ids
        @param context : standard Dictionary
        @return : True
        '''
        res_user_obj = self.pool.get('res.users')
        template_obj = self.pool.get('email.template')
        mail_mail = self.pool.get('mail.mail')
        holiday_master_ids = self.pool.get('holiday.master').search(cr, uid,
                                                                    [],
                                                            context=context)
        template_id = self.pool.get('ir.model.data').get_object(cr, uid,
                                            'meeting_reminder',
                                            'email_template_reminder_holiday',
                                            context=context)
        for holiday_data in self.browse(cr, uid, holiday_master_ids,
                                        context=context):
            cur_datetime = datetime.datetime.now().strftime(
                                            DEFAULT_SERVER_DATE_FORMAT)
            cur_datetime = datetime.datetime.strptime(cur_datetime, "%Y-%m-%d")
            if holiday_data.start_date:
                print "is start date"
                start_date = datetime.datetime.strptime(
                                                    holiday_data.start_date,
                                                    "%Y-%m-%d")
                diff = cur_datetime - start_date
                if diff:
                    str_diff = str(diff).split(' ')
                    if str_diff[0] == str(-1):
                        res_user_ids = res_user_obj.search(cr, uid, [],
                                                          context=context)
                        for user in res_user_obj.browse(cr, uid, res_user_ids,
                                                        context=context):
                            notified_users = [notified_user.partner_id.id
                              for notified_user in holiday_data.notified_users]
                            if user.partner_id.id not in notified_users:
                                template_values = template_obj.generate_email(
                                                          cr,
                                                          uid, template_id.id,
                                                          holiday_data.id,
                                                          context=context)
                                template_values.update({
                                            'email_to': user.partner_id.email})
                                msg_id = mail_mail.create(cr, uid,
                                                          template_values,
                                                          context=context)
                                mail_mail.send(cr, uid, [msg_id],
                                               context=context)
                                self.pool.get('notify.holiday').create(cr, uid,
                                           {'partner_id': user.partner_id.id,
                                            'email': user.partner_id.email,
                                            'holiday_id': holiday_data.id
                                            }, context=context)
        return True
