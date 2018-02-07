# -*- coding: utf-'8' "-*-"

import base64
try:
    import simplejson as json
except ImportError:
    import json
import logging
import urlparse
import werkzeug.urls
import urllib2

from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_payu_com.controllers.main import PayuController
from odoo import models, fields,api
from odoo.tools.float_utils import float_compare
import inspect


_logger = logging.getLogger(__name__)


class AcquirerPayu(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('payu_com', 'payu')])
    payu_email_account = fields.Char('Payu Email ID', required_if_provider='payu_com')
    payu_seller_account = fields.Char('Payu Merchant ID',
            help='The Merchant ID is used to ensure communications coming from Payu are valid and secured.')
    payu_api_username = fields.Char('Rest API Username')
    payu_api_password = fields.Char('Rest API Password')


    def _get_payu_urls(self,environment):
        """ Paypal URLS """
        if environment == 'prod':
            return {
                'payu_form_url': 'https://secure.payu.co.za/service/PayUAPI?wsdl',
            }
        else:
            return {
                'payu_form_url': 'https://staging.payu.co.za/service/PayUAPI?wsdl',
            }

    def _get_providers(self,*args, **kwargs):
        providers = super(AcquirerPayu, self)._get_providers()
        providers.append(('payu_com', 'payu'))
	
        return providers

    '''payu_email_account = fields.Char('Payu Email ID', required_if_provider='payu_com')
    payu_seller_account = fields.Char('Payu Merchant ID',
            help='The Merchant ID is used to ensure communications coming from Payu are valid and secured.')
    payu_api_username = fields.Char('Rest API Username')
    payu_api_password = fields.Char('Rest API Password')
    provider = fields.Selection(selection_add=[('payu_com', 'payu')])'''


    def _migrate_payu_account(self):
        """ COMPLETE ME """
        self.env.cr.execute('SELECT id, paypal_account FROM res_company')
        res = self.env.cr.fetchall()
        for (company_id, company_payu_account) in res:
            if company_payu_account:
                company_payu_ids = self.search([('company_id', '=', company_id), ('name', 'ilike', 'payu')], limit=1).ids
                if company_payu_ids:
                    self.write(company_payu_ids, {'payu_email_account': company_payu_account})
                else:
                    payu_view = self.env['ir.model.data'].get_object('payment_payu_com', 'payu_button')
                    self.create({
                        'name': 'payu.com',
                        'payu_email_account': company_payu_account,
                        'view_template_id': payu_view.id,
                    })
        return True


    @api.multi
    def payu_com_form_generate_values(self, values):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
	
        acquirer = self
        paypal_tx_values = dict(values)
        paypal_tx_values.update({
            #'cmd': '_xclick',
            #'business': acquirer.paypal_email_account,
            'item_name': values['reference'],
            'item_number': values['reference'],
            'amount':values['amount'],
            'currency_code': values['currency'] and values['currency'].name or '',
            'address1': values['partner_address'],
            'city': values.get('partner_city'),
            'country': values.get('partner_country') and values.get('partner_country').code or '',
            'state': values.get('partner_state') and (values.get('partner_state').code or values.get('partner_state').name) or '',
            'email': values.get('partner_email'),
            'zip_code': values.get('partner_zip'),
            'zip_code': values.get('partner_zip'),
            'first_name': values.get('partner_first_name'),
            'last_name': values.get('partner_last_name'),
            'return': '%s' % urlparse.urljoin(base_url, PayuController._return_url),
            #'notify_url': '%s' % urlparse.urljoin(base_url, PaypalController._notify_url),
            #'cancel_return': '%s' % urlparse.urljoin(base_url, PaypalController._cancel_url),
        })
        if acquirer.fees_active:
            paypal_tx_values['handling'] = '%.2f' % paypal_tx_values.pop('fees', 0.0)
        if paypal_tx_values.get('return_url'):
            paypal_tx_values['custom'] = json.dumps({'return_url': '%s' % paypal_tx_values.pop('return_url')})
        return paypal_tx_values


    def payu_com_get_form_action_url(self):
        acquirer = self
        return self._get_payu_urls(acquirer.environment)['payu_form_url']
