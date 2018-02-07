# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    margin = fields.Float('Margin')

    def _select(self):
        return super(AccountInvoiceReport, self)._select() + ", sub.margin / COALESCE(cr.rate, 1.0) AS margin"

    def _sub_select(self):
        return super(AccountInvoiceReport, self)._sub_select() + ", SUM(ail.margin) AS margin"
