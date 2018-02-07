# -*- coding: utf-8 -*-
import werkzeug

from odoo import SUPERUSER_ID
from odoo import http
from odoo.http import request
from odoo.tools.translate import _
from odoo.addons.website.models.website import slug
#from odoo.addons.web.controllers.main import login_redirect
import odoo.addons.website_sale.controllers.main as website_sale
from datetime import datetime


PPG = 20 # Products Per Page
PPR = 4  # Products Per Row


class WebsiteSale(website_sale.WebsiteSale):
     
    @http.route('/shop/payment/validate', type='http', auth="public", website=True)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        cr, uid, context = request.cr, request.uid, request.context
        email_act = None
        sale_order_obj = request.env['sale.order']
        email_obj = request.env['mail.template']
        if transaction_id is None:
            tx = request.website.sale_get_transaction()
        else:
            tx = request.env['payment.transaction'].sudo().browse(transaction_id)

        if sale_order_id is None:
            order = request.website.sale_get_order()
        else:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            assert order.id == request.session.get('sale_last_order_id')

        if not order or (order.amount_total and not tx):
            #return request.redirect('/shop')
	    return request.redirect('/shop/confirmation')

        if (not order.amount_total and not tx) or tx.state in ['pending', 'done']:
            if (not order.amount_total and not tx):
                # Orders are confirmed by payment transactions, but there is none for free orders,
                # (e.g. free events), so confirm immediately
                order.action_button_confirm()
            # send by email
         #   email_act = sale_order_obj.action_quotation_send(cr, SUPERUSER_ID, [order.id], context=request.context)
	    template_id = False
            if template_id:
                mail_message = template_id.send_mail(order.id) #email_obj.sudo().send_mail(template_id[0],order.id)
        elif tx and tx.state == 'cancel':
            # cancel the quotation
            sale_order_obj.sudo().action_cancel([order.id])

        # send the email
        #if email_act and email_act.get('context'):
        #    composer_values = {}
        #    email_ctx = email_act['context']
        #    public_id = request.website.user_id.id
        #    if uid == public_id:
        #        composer_values['email_from'] = request.website.user_id.company_id.email
        #    composer_id = request.registry['mail.compose.message'].create(cr, SUPERUSER_ID, composer_values, context=email_ctx)
        #    request.registry['mail.compose.message'].send_mail(cr, SUPERUSER_ID, [composer_id], context=email_ctx)

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()

        return request.redirect('/shop/confirmation')
