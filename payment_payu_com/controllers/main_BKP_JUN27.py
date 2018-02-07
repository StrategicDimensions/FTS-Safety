# -*- coding: utf-8 -*-

try:
    import simplejson as json
except ImportError:
    import json
import logging
import pprint
import urllib2
import werkzeug

from odoo import http, SUPERUSER_ID
from odoo.http import request

import suds
import os
from traceback import print_exc
from suds.client import Client
from suds.client import Client, sys
from suds.sax.element import Element
from suds.sax.attribute import Attribute
from suds.xsd.sxbasic import Import
from suds.wsse import UsernameToken, Security, Token
from flask import session
from datetime import datetime
from suds.plugin import MessagePlugin

_logger = logging.getLogger(__name__)

class MyPlugin(MessagePlugin):
     def __init__(self):
             self.last_sent_raw = None
             self.last_received_raw = None
     def sending(self, context):
             self.last_sent_raw = str(context.envelope)
     def received(self, context):
             self.last_received_raw = str(context.reply)



class PayuController(http.Controller):
    _notify_url = '/payment/payu_com/ipn/'
    _return_url = '/payment/payu_com/dpn/'
    _cancel_url = '/payment/payu_com/cancel/'

    def _get_return_url(self, **post):
        """ Extract the return URL from the data coming from payu.com . """
	
        return_url = post.pop('return_url', '')
        if not return_url:
            custom = json.loads(post.pop('custom', '{}'))
            return_url = custom.get('return_url', '/')
        return return_url

    @http.route('/payment/payu_com/ipn/', type='http', auth='none', methods=['POST'])
    def payu_com_ipn(self, **post):
        """ Paypal IPN. """
        _logger.info('Beginning Paypal IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        self.payu_com_validate_data(**post)
        return ''

    @http.route('/payment/payu_com/dpn', type='http', auth="public", methods=['POST','GET'], website=True)
    def payu_com_dpn(self, **post):
        """This method is used for getting response from Payu and create invoice automatically if successful"""
	sale_order_obj = request.env['sale.order']
        email_obj = request.env['mail.template']
        cr, uid, context = request.cr, request.uid, request.context
        transactionDetails = {}
        transactionDetails['store'] = {}
        transactionDetails['store']['soapUsername'] = 'Staging Integration Store 3'
        transactionDetails['store']['soapPassword'] = 'WSAUFbw6'
        transactionDetails['store']['safekey'] = '{07F70723-1B96-4B97-B891-7BF708594EEA}'
       
        transactionDetails['store']['environment'] = 'staging'

        transactionDetails['additionalInformation'] = {}
        
        transactionDetails['additionalInformation']['payUReference'] = post['PayUReference']
        try:
           result = self.payuMeaGetTransactionApiCall(transactionDetails)
        except Exception,e:
           werkzeug.utils.redirect('/shop/unsuccessful')
        payu_response = {}
        payu_response['REFERENCE'] = post['PayUReference']
        payu_response['gatewayReference'] = False
        payu_response['TRANSACTION_STATUS'] = ''
        if result:
            payu_response['TRANSACTION_STATUS'] = result['transactionState']
            payu_response['successful'] = result['successful']
            payu_response['AMOUNT'] = result['paymentMethodsUsed']['amountInCents']
            payu_response['RESULT_DESC'] = result['resultMessage']
            payu_response['TRANSACTION_ID'] = result['payUReference']
            try:
                payu_response['gatewayReference']=result['gatewayReference']
            except:
                payu_response['gatewayReference'] = False
            payu_response['sale_order'] = result['merchantReference']
            payment_status = False
            sale_order_id = request.env['sale.order'].sudo().search([('name','=',result['merchantReference'])])
           
            tx_id = request.env['payment.transaction'].sudo().search([('reference','=',result['merchantReference'])])
           
            tx = tx_id #request.env['payment.transaction'].sudo().browse(tx_id)
            #order = request.env['sale.order'].sudo().browse(sale_order_id)
	    if sale_order_id:
		sale_order_id.write({'ignore_check':True})
            if not sale_order_id or (sale_order_id.amount_total and not tx):
                return request.redirect('/shop')      
            if (not sale_order_id.amount_total and not tx) or tx.state in ['pending', 'done']:
                if (not sale_order_id.amount_total and not tx):
                    sale_order_id.action_button_confirm()
                email_act = sale_order_id.action_quotation_send()
            elif tx and tx.state == 'cancel':
		sale_order_id.action_cancel()
            elif tx and tx.state == 'draft':
                
                if result and payu_response['successful'] and payu_response['TRANSACTION_STATUS'] in ['SUCCESSFUL','PARTIAL_PAYMENT','OVER_PAYMENT']: 
			
		    transaction = tx.sudo().write({'state':'done','date_validate':datetime.now(),'acquirer_reference':result['payUReference']})
		    email_act = sale_order_id.action_quotation_send()                    
		    action_confirm_res = sale_order_id.action_confirm()
                    sale_order = sale_order_id.read([])
                    sale_adv_payment = {
                       'advance_payment_method':'all',
                    }
                    advanc_pay_id = request.env['sale.advance.payment.inv'].sudo().create(sale_adv_payment)

                    result = advanc_pay_id.with_context({'active_ids':[sale_order_id.id]}).create_invoices()
                    invoice_id = sale_order_id.read(['invoice_ids'])
		    inv_obj = request.env['account.invoice'].sudo().browse(invoice_id[0]['invoice_ids'])
		    result = inv_obj.action_invoice_open()
			
                    account_invoice = inv_obj.read([])
                    if account_invoice[0]['state']!='paid':
                        journal_ids = request.env['account.journal'].sudo().search([('code','=ilike','BNK1')],limit=1)
                        journal = journal_ids.read([])
			currency = request.env['res.currency'].sudo().search([('name','=','ZAR')],limit=1)
			method = request.env['account.payment.method'].sudo().search([('name','=','Manual')],limit=1)
			account_payment = {
			    'partner_id': sale_order[0]['partner_id'][0],
			    'partner_type':'customer',
			    'journal_id':journal_ids.id,
			    'invoice_ids':[(4,inv_obj.id,0)],
			    'amount':sale_order[0]['amount_total'],
			    'communication':inv_obj.number,
			    'currency_id':currency.id,
			    'payment_type':'inbound',
			    'payment_method_id':method.id
					}
			acc_payment = request.env['account.payment'].sudo().create(account_payment)
			acc_payment.post()	
                    return werkzeug.utils.redirect('/shop/confirmation')
                else:
                    return werkzeug.utils.redirect('/shop/unsuccessful')    
        return werkzeug.utils.redirect('/shop/unsuccessful')
        

    @http.route(['/shop/unsuccessful'], type='http', auth="public", website=True)
    def unsuccessful(self, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        cr, uid, context = request.cr, request.uid, request.context

        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
        else:
            return request.redirect('/shop')
        request.website.sale_reset()
        return request.render("payment_payu_com.unsuccessful", {'order': order})
        

    @http.route('/payment/payu_com/cancel', type='http', auth="none",methods=['POST','GET'])
    def payu_com_cancel(self, **post):
        """ When the user cancels its Payu payment: GET on this route """
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        
	
        return  werkzeug.utils.redirect('/shop/unsuccessful')

    @http.route('/shop/redirect_payu', type='http', auth='none', methods=['POST'])
    def redirect_payu(self, **post):

        transactionDetails = {}
        transactionDetails['store'] = {}
        transactionDetails['store']['soapUsername'] = 'Staging Integration Store 3'
        transactionDetails['store']['soapPassword'] = 'WSAUFbw6'
        transactionDetails['store']['safekey'] = '{07F70723-1B96-4B97-B891-7BF708594EEA}'

        transactionDetails['store']['environment'] = 'staging'
        amount = post['amount']
        if len(amount.split('.')[1])==1:
            amount=amount+'0'
            amount= amount.replace('.','')
        elif len(amount.split('.')[1])==2:
            amount= amount.replace('.','')

        transactionDetails['store']['TransactionType'] = 'PAYMENT';
        transactionDetails['basket'] = {}
        transactionDetails['basket']['description'] = 'Thirst'
        transactionDetails['basket']['amountInCents'] = amount
        #transactionDetails['basket']['currencyCode'] = post['c_currency_id']
        transactionDetails['basket']['currencyCode'] = post['currency']

	transactionDetails['additionalInformation'] = {}
        transactionDetails['additionalInformation']['merchantReference'] = post['reference'] #'10378546340'      

        transactionDetails['additionalInformation']['returnUrl'] =  'http://ftsliveclone.odoo.co.za/payment/payu_com/dpn'
        transactionDetails['additionalInformation']['cancelUrl'] =  'http://ftsliveclone.odoo.co.za/payment/payu_com/cancel'
        transactionDetails['additionalInformation']['supportedPaymentMethods'] = 'CREDITCARD'
        transactionDetails['additionalInformation']['demoMode'] = False
        transactionDetails['Stage'] = False

        transactionDetails['customer'] = {}
        transactionDetails['customer']['email'] = post['email']
        transactionDetails['customer']['firstName'] = post['first_name']
        transactionDetails['customer']['lastName'] = post['last_name']
        transactionDetails['customer']['mobile'] = post['phone']

        url = self.payuMeaSetTransactionApiCall(transactionDetails)

        return werkzeug.utils.redirect(url)

    
    def payuMeaSetTransactionApiCall(self,args):    
        if    (args['store']['environment'] == 'staging')    :
            urlToQuery = 'https://staging.payu.co.za/service/PayUAPI?wsdl'
        try:
	    plugin = MyPlugin()
            client = Client(urlToQuery, plugins=[plugin])
            #client = Client(urlToQuery, faults=False)
        except Exception, e:
	    #print e,'Exceptionnnnnnnnnn'

            return "http://ftsliveclone.odoo.co.za/shop/unsuccessful"
    #------------------------------------- CREATING CUSTOM HEADER--------------------------------------
    
        wsse = ('wsse','http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd')

        mustAttributeSecurity = Attribute('SOAP-ENV:mustUnderstand', '1')
        addressAttributeSecurity = Attribute('xmlns:wsse', 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd')
        AttributeUsernameToken1 = Attribute('wsu:Id','UsernameToken-9')
        addressAttributeUsernameToken = Attribute('xmlns:wsu','http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd')
        addressAttributePassword = Attribute('Type','http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText')

        msgUsername = Element('Username', ns=wsse).setText(args['store']['soapUsername'])
        msgPassword = Element('Password', ns=wsse).setText(args['store']['soapPassword']).append(addressAttributePassword)

        msgUsernameToken = Element('UsernameToken', ns=wsse)
        msgUsernameToken.append(AttributeUsernameToken1)
        msgUsernameToken.append(addressAttributeUsernameToken)
        msgUsernameToken.insert(msgPassword).insert(msgUsername)
    
        msgSecurity = Element('Security', ns=wsse).addPrefix(p='SOAP-ENC', u='http://www.w3.org/2003/05/soap-encoding')
        msgSecurity.append(mustAttributeSecurity)
        msgSecurity.append(addressAttributeSecurity)
        msgSecurity.insert(msgUsernameToken)

        client.set_options(soapheaders=[msgSecurity])

    #------------------------------------- CREATING SOAP CALL DETAILS HERE--------------------------------------    
        transaction = {}
        transaction['Api'] = 'ONE_ZERO';
        transaction['Safekey'] = args['store']['safekey'];
        transaction['TransactionType'] = 'PAYMENT';    
        transaction['AdditionalInformation'] = args['additionalInformation']            
        transaction['Basket'] = args['basket']    
        transaction['Customer'] = args['customer']    
    
    #------------------------------------- DOING SOAP CALL HERE--------------------------------------
        try:
            setTransaction = client.service.setTransaction(** transaction)
        except Exception, e:
       
            print_exc()
        s= plugin.last_received_raw #s=client.last_received()	
        import xmltodict
        dic = xmltodict.parse(str(s)) 
     
        number = dic['soap:Envelope']['soap:Body']['ns2:setTransactionResponse']['return']['payUReference']        
        url = 'https://staging.payu.co.za/rpp.do'+'?PayUReference='+str(number)
        return url

    def payuMeaGetTransactionApiCall(self,args):

        #urlToQuery = 'https://secure.payu.co.za/service/PayUAPI?wsdl'
        if      (args['store']['environment'] == 'staging')     :
                urlToQuery = 'https://staging.payu.co.za/service/PayUAPI?wsdl'
        
	plugin = MyPlugin()
        client = Client(urlToQuery, plugins=[plugin]) 
        #client = Client(urlToQuery, faults=False)
        #------------------------------------- CREATING CUSTOM HEADER--------------------------------------
        wsse = ('wsse','http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd')

        mustAttributeSecurity = Attribute('SOAP-ENV:mustUnderstand', '1')
        addressAttributeSecurity = Attribute('xmlns:wsse', 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd')
        AttributeUsernameToken1 = Attribute('wsu:Id','UsernameToken-9')
        addressAttributeUsernameToken = Attribute('xmlns:wsu','http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd')
        addressAttributePassword = Attribute('Type','http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText')

        msgUsername = Element('Username', ns=wsse).setText(args['store']['soapUsername'])
        msgPassword = Element('Password', ns=wsse).setText(args['store']['soapPassword']).append(addressAttributePassword)

        msgUsernameToken = Element('UsernameToken', ns=wsse)
        msgUsernameToken.append(AttributeUsernameToken1)
        msgUsernameToken.append(addressAttributeUsernameToken)
        msgUsernameToken.insert(msgPassword).insert(msgUsername)

        msgSecurity = Element('Security', ns=wsse).addPrefix(p='SOAP-ENC', u='http://www.w3.org/2003/05/soap-encoding')
        msgSecurity.append(mustAttributeSecurity)
        msgSecurity.append(addressAttributeSecurity)
        msgSecurity.insert(msgUsernameToken)
        
        client.set_options(soapheaders=[msgSecurity])

        #------------------------------------- CREATING SOAP CALL DETAILS HERE--------------------------------------    
        transaction = {}
        transaction['Api'] = 'ONE_ZERO';
        transaction['Safekey'] = args['store']['safekey'];
        transaction['AdditionalInformation'] = args['additionalInformation']
        #------------------------------------- DOING SOAP CALL HERE--------------------------------------
        try:
                setTransaction = client.service.getTransaction(** transaction)
        except Exception, e:
                print_exc()
        s= plugin.last_received_raw #s=client.last_received()
        transactionState=''
        successful_status=False
        import xmltodict  
        if s:
            dic = xmltodict.parse(str(s))
            dic['soap:Envelope']['soap:Body']['ns2:getTransactionResponse']['return']['displayMessage']
            payUReference = dic['soap:Envelope']['soap:Body']['ns2:getTransactionResponse']['return']['payUReference']
            successful_status = dic['soap:Envelope']['soap:Body']['ns2:getTransactionResponse']['return']['successful']
            transactionState = dic['soap:Envelope']['soap:Body']['ns2:getTransactionResponse']['return']['transactionState']
        if transactionState == 'SUCCESSFUL' and successful_status:
            return dic['soap:Envelope']['soap:Body']['ns2:getTransactionResponse']['return']
        elif transactionState == 'AWAITING_PAYMENT':
            return dic['soap:Envelope']['soap:Body']['ns2:getTransactionResponse']['return']
        else:
            return False
