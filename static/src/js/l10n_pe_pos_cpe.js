odoo.define('l10n_pe_pos_cpe.l10n_pe_pos_cpe', function (require) {
"use strict";

var models = require('point_of_sale.models');
var screens = require('point_of_sale.screens');
var PosDB =require('point_of_sale.DB');
var core    = require('web.core');

var _t      = core._t;

var PosModelSuper = models.PosModel;
var PosDBSuper = PosDB;
var OrderSuper = models.Order;

models.load_fields("res.company", ["sunat_amount"]);

models.Order = models.Order.extend({
    get_cpe_type: function () {
        var journal_id=this.get_sale_journal();
        if (!journal_id){
            return false;
        }
        var journal = this.pos.db.get_journal_id(journal_id);
        return journal.pe_invoice_code;
    },
    get_cpe_qr: function(){
        var res=[]
        res.push(this.pos.company.vat && this.pos.company.vat.slice(2, this.pos.company.vat.length) || '');
        res.push(this.get_cpe_type() || '');
        res.push(this.get_number() || '');
        res.push(this.get_total_tax() || '');
        res.push(this.get_total_with_tax() || '');
        res.push(new Date().toString("yyyy-MM-dd"));
        res.push(this.get_doc_type() || '-');
        res.push(this.get_doc_number() || '-');
        var qr_string=res.join('|');
        return qr_string;
    },
    export_as_JSON: function() {
        var res = OrderSuper.prototype.export_as_JSON.apply(this, arguments);
        res['pe_invoice_date']=moment(new Date().getTime()).format('YYYY-MM-DD HH:mm:ss');
        return res;
    },
});

screens.PaymentScreenWidget.include({
    validate_journal_invoice: function() {
        var res = this._super()
        var order = this.pos.get_order();
        if (res) {
            return res;
        }
        self = this;
        var doc_type = order.get_doc_type();
        var doc_number = order.get_doc_number();
        var is_validate = this.pos.validate_pe_doc(doc_type, doc_number);
        var cpe_type = order.get_cpe_type();
        var err_lines = false;
        order.orderlines.each(_.bind( function(item) {
            if ((item.get_quantity() == 0 || item.get_unit_price() == 0) && !err_lines) {
                err_lines = true;
                return err_lines;    
            }
            
        }, this));
        if (err_lines){
            self.gui.show_popup('error',_t('The quantity or the unit price must be greater than 0'));
            res = true;
        }
        if (self.pos.company.sunat_amount< order.get_total_with_tax() && !doc_type && !doc_number){
            self.gui.show_popup('confirm',{
                        'title': _t('An anonymous order cannot be invoiced'),
                        'body': _t('You need to select the customer with RUC/DNI before you can invoice an order.'),
                        confirm: function(){
                            self.gui.show_screen('clientlist');
                        },
                    });
            res = true;
        }

        if ( ['1', '6'].indexOf(doc_type)!=-1 && !is_validate){
            self.gui.show_popup('confirm',{
                        'title': _t('Please select the Customer'),
                        'body': _t('You must select the customer with valid RUC/DNI before you can invoice an order.'),
                        confirm: function(){
                            self.gui.show_screen('clientlist');
                        },
                    });
            res = true;
        }
        /*if ( ['01', '03'].indexOf(cpe_type)==-1){
            this.gui.show_popup('error',_t('You can not issue that type of voucher. Set up your journal well'));
            res = true;
        }*/
        if (cpe_type=='01' && doc_type!='6') {
            self.gui.show_popup('confirm',{
                        'title': _t('Please select the Customer'),
                        'body': _t('You must select the customer with RUC before you can invoice an order.'),
                        confirm: function(){
                            self.gui.show_screen('clientlist');
                        },
                    });
            res = true;
        }
        if (cpe_type=='03' && doc_type=='6') {
            self.gui.show_popup('confirm',{
                        'title': _t('Please select the Customer'),
                        'body': _t('You must select the customer with DNI or another before you can invoice an order.'),
                        confirm: function(){
                            self.gui.show_screen('clientlist');
                        },
                    });
            res = true;
        }
        return res;
        
    },
});

screens.ReceiptScreenWidget.include({
    render_receipt: function() {
        var order = this.pos.get('selectedOrder');
        this._super();
        if (order.get_cpe_type()){
            var qr_string=order.get_cpe_qr(); 
            var qrcode = new QRCode(document.getElementById("qr-code"), { width : 128, height : 128, correctLevel : QRCode.CorrectLevel.Q });
            qrcode.makeCode(qr_string);
            var blob = new Blob([JSON.stringify(order.export_as_JSON())], {type: "text/plain;charset=utf-8"});
            saveAs(blob, order.number+".json");
        }

    }
});

});
