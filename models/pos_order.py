# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PosOrder(models.Model):
    _inherit = "pos.order"

    pe_credit_note_code = fields.Selection(selection="_get_pe_crebit_note_type", string="Credit Note Code")
    #pe_is_refund = fields.Boolean("Is Refund")
    pe_invoice_type = fields.Selection([("annul", "Annul"),("refund","Credit Note")], "Invoice Type")
    pe_motive = fields.Char("Reason for Credit Note")
    pe_license_plate = fields.Char("License Plate", size=10)
    pe_invoice_date = fields.Datetime("Invoice Date Time", copy = False)
    
    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        res['pe_invoice_date']=ui_order.get('pe_invoice_date', False)
        return res
    
    @api.model
    def _get_pe_crebit_note_type(self):
        return self.env['pe.datas'].get_selection("PE.CPE.CATALOG9")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        super(PosOrder, self)._onchange_partner_id()
        self.ensure_one()
        if self.partner_id and self.env.context.get('force_pe_journal'):
            partner_id = self.partner_id.parent_id or self.partner_id
            if partner_id.doc_type in ["6"]:
                journal_id=self.env['account.journal'].search([('company_id','=',self.company_id.id), 
                                                               ('pe_invoice_code', '=', '01'),
                                                               ('type', '=', 'sale')], limit=1)
                if journal_id:
                    self.invoice_journal=journal_id.id
            else:
                journal_id=self.env['account.journal'].search([('company_id','=',self.company_id.id), 
                                                               ('pe_invoice_code', '=', '03'),
                                                               ('type', '=', 'sale')], limit=1)
                self.invoice_journal=journal_id.id or self.partner_id.property_product_pricelist.id
    
    @api.multi
    def refund(self):
        res = super(PosOrder, self).refund()
        order_id = res.get("res_id", False)
        if order_id:
            for order in self.browse([order_id]):
                order.pe_invoice_type = self.env.context.get("default_pe_invoice_type", False)
                if order.pe_invoice_type == 'annul' and order.refund_invoice_id:
                    if order.refund_invoice_id.state == 'open':
                        order.invoice_journal = order.session_id.config_id.journal_id.id
                    else:
                        raise ValidationError(_("You can not cancel the invoice, you must create a credit note"))
                else:
                    invoice_journal = self.invoice_journal.credit_note_id and self.invoice_journal.credit_note_id.id or self.invoice_journal.id  
                    order.invoice_journal = invoice_journal or False
        return res
    
    def _prepare_invoice(self):
        res = super(PosOrder, self)._prepare_invoice()
        res['pe_credit_note_code'] = self.pe_credit_note_code or False
        res['pe_invoice_date'] = self.pe_invoice_date or False
        if self.pe_invoice_type == 'refund':
            res['name'] = self.pe_motive or False
        return res
    
    @api.multi
    def action_pos_order_invoice(self):
        for order in self:
            if order.pe_invoice_type == 'annul':
                raise ValidationError(_("The invoice was canceled, you can not create a credit note"))
        return super(PosOrder, self).action_pos_order_invoice()
        