# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class SaleReport(models.Model):
    _name = "amazon.sales.report"
    _description = "Sales Orders Statistics"
    _auto = False
    _order = 'date desc'

#     name = fields.Char('Order Reference', readonly=True)
    date = fields.Datetime('Date Order', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
#     product_uom = fields.Many2one('product.uom', 'Unit of Measure', readonly=True)
    product_uom_qty = fields.Float('# of Qty', readonly=True)
    amazon_shop = fields.Many2one('sale.shop',string="Amazon Shop")
    amazon_instance_id = fields.Many2one('amazon.seller.instance',string="Amazon Instance")
#     qty_delivered = fields.Float('Qty Delivered', readonly=True)
#     qty_to_invoice = fields.Float('Qty To Invoice', readonly=True)
#     qty_invoiced = fields.Float('Qty Invoiced', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    price_total = fields.Float('Total', readonly=True)
#     price_subtotal = fields.Float('Untaxed Total', readonly=True)
#     product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)
    amazon_categ_id = fields.Many2one('product.category', 'Amazon Product Category', readonly=True)
#     nbr = fields.Integer('# of Lines', readonly=True)
#     pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
#     analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', readonly=True, oldname='section_id')
    country_id = fields.Many2one('res.country', 'Partner Country', readonly=True)
#     commercial_partner_id = fields.Many2one('res.partner', 'Commercial Entity', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Sales Done'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True)
#     weight = fields.Float('Gross Weight', readonly=True)
#     volume = fields.Float('Volume', readonly=True)


    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            min(l.id) as id,
            l.product_id as product_id,
            t.uom_id as product_uom,
            sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
            sum(l.qty_delivered / u.factor * u2.factor) as qty_delivered,
            sum(l.qty_invoiced / u.factor * u2.factor) as qty_invoiced,
            sum(l.qty_to_invoice / u.factor * u2.factor) as qty_to_invoice,
            sum(l.price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as price_total,
            sum(l.price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as price_subtotal,
            sum(l.untaxed_amount_to_invoice / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as untaxed_amount_to_invoice,
            sum(l.untaxed_amount_invoiced / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as untaxed_amount_invoiced,
            count(*) as nbr,
            s.name as name,
            s.date_order as date,
            s.confirmation_date as confirmation_date,
            s.state as state,
            s.partner_id as partner_id,
            s.user_id as user_id,
            s.company_id as company_id,
            ss.amazon_instance_id as amazon_instance_id,
            s.shop_id as amazon_shop,
            extract(epoch from avg(date_trunc('day',s.date_order)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
            t.categ_id as categ_id,
            s.pricelist_id as pricelist_id,
            s.analytic_account_id as analytic_account_id,
            s.team_id as team_id,
            p.product_tmpl_id,
            partner.country_id as country_id,
            partner.commercial_partner_id as commercial_partner_id,
            sum(p.weight * l.product_uom_qty / u.factor * u2.factor) as weight,
            sum(p.volume * l.product_uom_qty / u.factor * u2.factor) as volume,
            l.discount as discount,
            sum((l.price_unit * l.discount / 100.0 / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END)) as discount_amount,
            s.id as order_id
        """

        for field in fields.values():
            select_ += field

        from_ = """
                sale_order_line l
                      join sale_order s on (l.order_id=s.id)
                      join sale_shop ss on (s.shop_id = ss.id and ss.amazon_shop = true)
                      join amazon_seller_instance ama on (ss.amazon_instance_id=ama.id)
                      join res_partner partner on s.partner_id = partner.id
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join uom_uom u on (u.id=l.product_uom)
                    left join uom_uom u2 on (u2.id=t.uom_id)
                    left join product_pricelist pp on (s.pricelist_id = pp.id)
                %s
        """ % from_clause

        groupby_ = """
            l.product_id,
            l.order_id,
            t.uom_id,
            t.categ_id,
            s.name,
            s.date_order,
            s.confirmation_date,
            s.partner_id,
            s.user_id,
            s.state,
            s.company_id,
            s.pricelist_id,
            s.analytic_account_id,
            s.team_id,
            p.product_tmpl_id,
            ss.id,
            ss.amazon_instance_id,
            partner.country_id,
            partner.commercial_partner_id,
            l.discount,
            s.id %s
        """ % (groupby)

        return '%s (SELECT %s FROM %s WHERE l.product_id IS NOT NULL GROUP BY %s)' % (with_, select_, from_, groupby_)

#    @api.model_cr
    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))


#     def _select(self):
#         select_str = """
#             WITH currency_rate as (%s)
#              SELECT min(l.id) as id,
#                     l.product_id as product_id,
#                     t.uom_id as product_uom,
#                     sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
#                     sum(l.qty_delivered / u.factor * u2.factor) as qty_delivered,
#                     sum(l.qty_invoiced / u.factor * u2.factor) as qty_invoiced,
#                     sum(l.qty_to_invoice / u.factor * u2.factor) as qty_to_invoice,
#                     sum(l.price_total / COALESCE(cr.rate, 1.0)) as price_total,
#                     sum(l.price_subtotal / COALESCE(cr.rate, 1.0)) as price_subtotal,
#                     count(*) as nbr,
#                     s.name as name,
#                     s.date_order as date,
#                     s.state as state,
#                     s.partner_id as partner_id,
#                     s.user_id as user_id,
#                     s.company_id as company_id,
#                     ss.amazon_instance_id as amazon_instance_id,
#                     s.shop_id as amazon_shop,
#                     extract(epoch from avg(date_trunc('day',s.date_order)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
#                     t.amazon_categ_id as amazon_categ_id,
#                     s.pricelist_id as pricelist_id,
#                     s.project_id as analytic_account_id,
#                     s.team_id as team_id,
#                     p.product_tmpl_id,
#                     partner.country_id as country_id,
#                     partner.commercial_partner_id as commercial_partner_id,
#                     sum(p.weight * l.product_uom_qty / u.factor * u2.factor) as weight,
#                     sum(p.volume * l.product_uom_qty / u.factor * u2.factor) as volume
#         """ % self.env['res.currency']._select_companies_rates()
#         return select_str
#
#     def _from(self):
#         from_str = """
#                 sale_order_line l
#                       join sale_order s on (l.order_id=s.id)
#                       join sale_shop ss on (s.shop_id = ss.id and ss.amazon_shop = true)
#                       join amazon_seller_instance ama on (ss.amazon_instance_id=ama.id)
#                       join res_partner partner on s.partner_id = partner.id
#                         left join product_product p on (l.product_id=p.id)
#                             left join product_template t on (p.product_tmpl_id=t.id)
#                     left join product_uom u on (u.id=l.product_uom)
#                     left join product_uom u2 on (u2.id=t.uom_id)
#                     left join product_pricelist pp on (s.pricelist_id = pp.id)
#                     left join currency_rate cr on (cr.currency_id = pp.currency_id and
#                         cr.company_id = s.company_id and
#                         cr.date_start <= coalesce(s.date_order, now()) and
#                         (cr.date_end is null or cr.date_end > coalesce(s.date_order, now())))
#
#         """
#         return from_str
#
#     def _group_by(self):
#         group_by_str = """
#             GROUP BY l.product_id,
#                     l.order_id,
#                     t.uom_id,
#                     t.amazon_categ_id,
#                     s.name,
#                     s.date_order,
#                     s.partner_id,
#                     s.user_id,
#                     s.state,
#                     s.company_id,
#                     s.pricelist_id,
#                     s.project_id,
#                     s.team_id,
#                     s.shop_id,
#                     p.product_tmpl_id,
#                     ss.amazon_instance_id,
#                     partner.country_id,
#                     partner.commercial_partner_id
#         """
#         return group_by_str
#
#     @api.model_cr
#     def init(self):
#         # self._table = sale_report
#         tools.drop_view_if_exists(self.env.cr, self._table)
#         q = """CREATE or REPLACE VIEW %s as (
#             %s
#             FROM ( %s )
#             %s
#             )""" % (self._table, self._select(), self._from(), self._group_by())
#         print (q)
#         self.env.cr.execute( q)






    # def _select(self):
    #     select_str = """
    #         WITH currency_rate as (%s)
    #          SELECT min(l.id) as id,
    #                 l.product_id as product_id,
    #                 t.uom_id as product_uom,
    #                 sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
    #                 sum(l.qty_delivered / u.factor * u2.factor) as qty_delivered,
    #                 sum(l.qty_invoiced / u.factor * u2.factor) as qty_invoiced,
    #                 sum(l.qty_to_invoice / u.factor * u2.factor) as qty_to_invoice,
    #                 sum(l.price_total / COALESCE(cr.rate, 1.0)) as price_total,
    #                 sum(l.price_subtotal / COALESCE(cr.rate, 1.0)) as price_subtotal,
    #                 sum(l.amt_to_invoice / COALESCE(cr.rate, 1.0)) as amt_to_invoice,
    #                 sum(l.amt_invoiced / COALESCE(cr.rate, 1.0)) as amt_invoiced,
    #                 count(*) as nbr,
    #                 s.name as name,
    #                 s.date_order as date,
    #                 s.confirmation_date as confirmation_date,
    #                 s.state as state,
    #                 s.partner_id as partner_id,
    #                 s.user_id as user_id,
    #                 s.company_id as company_id,
    #                 extract(epoch from avg(date_trunc('day',s.date_order)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
    #                 t.categ_id as categ_id,
    #                 s.pricelist_id as pricelist_id,
    #                 s.analytic_account_id as analytic_account_id,
    #                 s.team_id as team_id,
    #                 p.product_tmpl_id,
    #                 partner.country_id as country_id,
    #                 partner.commercial_partner_id as commercial_partner_id,
    #                 sum(p.weight * l.product_uom_qty / u.factor * u2.factor) as weight,
    #                 sum(p.volume * l.product_uom_qty / u.factor * u2.factor) as volume
    #     """ % self.env['res.currency']._select_companies_rates()
    #     return select_str
    #
    # def _from(self):
    #     from_str = """
    #             sale_order_line l
    #                   join sale_order s on (l.order_id=s.id)
    #                   join res_partner partner on s.partner_id = partner.id
    #                     left join product_product p on (l.product_id=p.id)
    #                         left join product_template t on (p.product_tmpl_id=t.id)
    #                 left join product_uom u on (u.id=l.product_uom)
    #                 left join product_uom u2 on (u2.id=t.uom_id)
    #                 left join product_pricelist pp on (s.pricelist_id = pp.id)
    #                 left join currency_rate cr on (cr.currency_id = pp.currency_id and
    #                     cr.company_id = s.company_id and
    #                     cr.date_start <= coalesce(s.date_order, now()) and
    #                     (cr.date_end is null or cr.date_end > coalesce(s.date_order, now())))
    #     """
    #     return from_str
    #
    # def _group_by(self):
    #     group_by_str = """
    #         GROUP BY l.product_id,
    #                 l.order_id,
    #                 t.uom_id,
    #                 t.categ_id,
    #                 s.name,
    #                 s.date_order,
    #                 s.confirmation_date,
    #                 s.partner_id,
    #                 s.user_id,
    #                 s.state,
    #                 s.company_id,
    #                 s.pricelist_id,
    #                 s.analytic_account_id,
    #                 s.team_id,
    #                 p.product_tmpl_id,
    #                 partner.country_id,
    #                 partner.commercial_partner_id
    #     """
    #     return group_by_str
    #
    # @api.model_cr
    # def init(self):
    #     # self._table = sale_report
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
    #         %s
    #         FROM ( %s )
    #         %s
    #         )""" % (self._table, self._select(), self._from(), self._group_by()))
    #
