from odoo import fields,models,api,_
from odoo.exceptions import ValidationError
 
class ProductTemplate(models.Model):
   _inherit = 'product.template'

   product_tags = fields.Selection([('stock','Stock Products'),('nonstock','Non Stock Products'),('core','Core Products'),('noncore','Non Core Products')],default='stock',string="Product Tags")
   type = fields.Selection([
        ('consu', 'Consumable'),
        ('service','Service'),('product', 'Stockable Product')], string='Product Type', default='product', required=True,
        help='A stockable product is a product for which you manage stock. The "Inventory" app has to be installed.\n'
             'A consumable product, on the other hand, is a product for which stock is not managed.\n'
             'A service is a non-material product you provide.\n'
             'A digital content is a non-material product you sell online. The files attached to the products are the one that are sold on '
             'the e-commerce such as e-books, music, pictures,... The "Digital Product" module has to be installed.')

   _sql_constraints = [
        ('default_code_uniq', 'unique(default_code)', _("Internal Reference can only be assigned to one productttt !")),
    ]


   @api.model
   def create(self,values):
        if values.get('default_code'):
            def_code_search = self.env['product.template'].search([('default_code','=',values.get('default_code'))])
            if def_code_search:
                raise ValidationError('Internal Reference can only be assigned to one product !')
        return super(ProductTemplate,self).create(values)

   @api.multi
   def write(self,values):
        if values.get('default_code'):
            def_code_search = self.env['product.template'].search([('default_code','=',values.get('default_code'))])
            if def_code_search:
                raise ValidationError('Internal Reference can only be assigned to one product !')
        return super(ProductTemplate,self).write(values)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    _sql_constraints = [
        ('default_code_uniq', 'unique(default_code)', _("Internal Reference can only be assigned to one product !")),
    ]


    @api.model
    def create(self,values):
        if values.get('default_code'):
            def_code_search = self.env['product.product'].search([('default_code','=',values.get('default_code'))])
            if def_code_search:
                raise ValidationError('Internal Reference can only be assigned to one product !')
        return super(ProductProduct,self).create(values)

    @api.multi
    def write(self,values):
        if values.get('default_code'):
            def_code_search = self.env['product.product'].search([('default_code','=',values.get('default_code'))])
            if def_code_search:
                raise ValidationError('Internal Reference can only be assigned to one product !')
        return super(ProductProduct,self).write(values)

