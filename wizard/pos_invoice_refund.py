# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class AccountInvoiceRefund(models.TransientModel):
    _name = "pos.invoice.refund.wizard"
    
    @api.model
    def _default_order_id(self):
        return self._context.get('active_ids', False) and self._context.get('active_ids', False)[0] or False
    
    type = fields.Selection([("annul", "Annul"),("refund","Credit Note")], "Type", default='annul')
    order_id = fields.Many2one('pos.order', string='POS Order', readonly=True, default=_default_order_id, required=True )
    pe_credit_note_code = fields.Selection(selection="_get_pe_crebit_note_type", string="Credit Note Code")
    
    @api.model
    def _get_pe_crebit_note_type(self):
        return self.env['pe.datas'].get_selection("PE.CPE.CATALOG9")
    
    @api.one
    def pos_refund(self):
        res = self.order_id.refund()
        order_id = res.get("res_id", False)
        res['target'] = 'self'
        #action = self.env.ref('point_of_sale.action_pos_pos_form').read()[0]
        #action['views'] = [(self.env.ref('point_of_sale.view_pos_pos_form').id, 'form')]
        #action['res_id'] = order_id
        #return action
        if order_id:
            for order in self.env['pos.order'].browse([order_id]):
                order.pe_credit_note_code = self.pe_credit_note_code
                order.pe_is_refund = self.type == "refund" and True or False
        if self.type == 'annul':
            if self.order_id.invoice_id.state == 'open':
                self.order_id.invoice_id.sudo().action_cancel()
                order_id.account_move = False
        return res