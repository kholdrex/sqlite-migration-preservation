"""Mappings from the shared operation product to additional migration APIs."""
from .matrix_spec import DRIZZLE, fixture

OPERATIONS = tuple(dict.fromkeys((*DRIZZLE, 'change_default', 'add_reference',
                                 'add_timestamps', 'add_check_constraint', 'remove_check_constraint')))


def orm_fixture(framework, operation, context):
    return fixture(framework, operation, context)


def django_models(op, ctx, after, database_cascade=False):
    """Model state excludes externally installed triggers, indexes and views."""
    def field(kind='TextField', **kwargs):
        return f'models.{kind}(' + ', '.join(f'{k}={v!r}' for k, v in kwargs.items()) + ')'

    value = dict(null=not ((op == 'drop_not_null' and not after) or (op == 'set_not_null' and after)))
    if (op in ('drop_default', 'change_default') and not after):
        value['db_default'] = '5'
    if op in ('set_default', 'change_default') and after:
        value['db_default'] = '9'
    value['unique'] = (op == 'drop_unique' and not after) or (op == 'add_unique' and after)
    columns = {'id': field('IntegerField', primary_key=True), 'payload': field(null=True)}
    if not (op == 'drop_column' and after):
        columns['renamed_value' if op == 'rename_column' and after else 'value'] = field(
            'IntegerField' if op == 'change_type' and after else 'TextField', **value)
    constrained = (op == 'drop_foreign_key' and not after) or (op == 'add_foreign_key' and after)
    columns['tenant'] = "models.ForeignKey('Tenant', on_delete=models.DO_NOTHING, null=True, db_column='tenant_id', db_index=False, db_constraint=" + repr(constrained) + ')'
    if ctx == 'C8':
        columns['ancestor'] = "models.ForeignKey('Tenant', on_delete=models." + ("DB_CASCADE" if database_cascade else "CASCADE") + ", null=True, db_column='ancestor_id', db_index=False, related_name='+')"
    if after and op == 'add_column':
        columns['note'] = field(null=True)
    if after and op == 'add_reference':
        columns['owner'] = "models.ForeignKey('Tenant', on_delete=models.DO_NOTHING, null=True, db_column='owner_id', db_index=False, related_name='+')"
    if after and op == 'add_timestamps':
        columns.update({c: field('DateTimeField', null=True) for c in ('created_at', 'updated_at')})
    indexes = ["models.Index(fields=['payload'], name='idx_declared')"]
    if (op == 'drop_index' and not after) or (op == 'add_index' and after):
        indexes.append("models.Index(fields=['value'], name='idx_operation')")
    constraints = []
    if (op == 'remove_check_constraint' and not after) or (op == 'add_check_constraint' and after):
        constraints.append("models.CheckConstraint(condition=models.Q(value__gt=0), name='positive_value')")
    source = "from django.db import models\n\nclass Tenant(models.Model):\n    id = models.IntegerField(primary_key=True)\n    payload = models.TextField(null=True)\n    class Meta:\n        db_table = 'tenants'\n\nclass Parent(models.Model):\n"
    source += ''.join(f'    {name} = {definition}\n' for name, definition in columns.items())
    table = 'renamed_parents' if op == 'rename_table' and after else 'parents'
    source += f'    class Meta:\n        db_table = {table!r}\n        indexes = [{", ".join(indexes)}]\n        constraints = [{", ".join(constraints)}]\n'
    return source


def alembic_operation(op, mode):
    operations = {
        'add_column': "batch.add_column(sa.Column('note', sa.Text()))",
        'drop_column': "batch.drop_column('value')",
        'rename_column': "batch.alter_column('value', new_column_name='renamed_value')",
        'change_type': "batch.alter_column('value', type_=sa.Integer())",
        'set_not_null': "batch.alter_column('value', nullable=False)",
        'drop_not_null': "batch.alter_column('value', nullable=True)",
        'set_default': "batch.alter_column('value', server_default=sa.text(\"'9'\"))",
        'change_default': "batch.alter_column('value', server_default=sa.text(\"'9'\"))",
        'drop_default': "batch.alter_column('value', server_default=None)",
        'add_foreign_key': "batch.create_foreign_key('fk_tenant', 'tenants', ['tenant_id'], ['id'])",
        'drop_foreign_key': "batch.drop_constraint('fk_tenant', type_='foreignkey')",
        'add_unique': "batch.create_unique_constraint('parents_value_unique', ['value'])",
        'drop_unique': "batch.drop_index('parents_value_unique')",
        'add_index': "batch.create_index('idx_operation', ['value'])",
        'drop_index': "batch.drop_index('idx_operation')",
        'add_check_constraint': "batch.create_check_constraint('positive_value', 'CAST(value AS INTEGER) > 0')",
        'remove_check_constraint': "batch.drop_constraint('positive_value', type_='check')",
        'add_reference': "batch.add_column(sa.Column('owner_id', sa.Integer()))\n        batch.create_foreign_key('fk_owner', 'tenants', ['owner_id'], ['id'])",
        'add_timestamps': "batch.add_column(sa.Column('created_at', sa.DateTime()))\n        batch.add_column(sa.Column('updated_at', sa.DateTime()))",
    }
    if op == 'rename_table':
        return "    op.rename_table('parents', 'renamed_parents')\n"
    return f"    with op.batch_alter_table('parents', recreate={mode!r}) as batch:\n        {operations[op]}\n"


def prisma_schema(op, ctx, after):
    table = 'renamed_parents' if op == 'rename_table' and after else 'parents'
    lines = ['datasource db {', '  provider = "sqlite"', '}', '', 'model Tenant {',
             '  id Int @id', '  payload String?', '  @@map("tenants")']
    constrained = (op == 'drop_foreign_key' and not after) or (op == 'add_foreign_key' and after)
    if constrained:
        lines.append('  parents Parent[] @relation("tenant")')
    if ctx == 'C8':
        lines.append('  descendants Parent[] @relation("ancestor")')
    if op == 'add_reference' and after:
        lines.append('  owned Parent[] @relation("owner")')
    lines += ['}', '', 'model Parent {', '  id Int @id', '  payload String?', '  tenant_id Int?']
    if not (op == 'drop_column' and after):
        name = 'renamed_value' if op == 'rename_column' and after else 'value'
        kind = 'Int' if op == 'change_type' and after else 'String'
        nullable = not ((op == 'drop_not_null' and not after) or (op == 'set_not_null' and after))
        value = f'  {name} {kind}{"?" if nullable else ""}'
        if op in ('change_default', 'drop_default') and not after:
            value += ' @default("5")'
        if op in ('change_default', 'set_default') and after:
            value += ' @default("9")'
        if (op == 'drop_unique' and not after) or (op == 'add_unique' and after):
            value += ' @unique(map: "parents_value_unique")'
        lines.append(value)
    if constrained:
        lines.append('  tenant Tenant? @relation("tenant", fields: [tenant_id], references: [id], onDelete: NoAction, onUpdate: NoAction)')
    if ctx == 'C8':
        lines += ['  ancestor_id Int?', '  ancestor Tenant? @relation("ancestor", fields: [ancestor_id], references: [id], onDelete: Cascade, onUpdate: NoAction)']
    if after and op == 'add_column':
        lines.append('  note String?')
    if after and op == 'add_reference':
        lines += ['  owner_id Int?', '  owner Tenant? @relation("owner", fields: [owner_id], references: [id], onDelete: NoAction, onUpdate: NoAction)']
    if after and op == 'add_timestamps':
        lines += ['  created_at DateTime?', '  updated_at DateTime?']
    if ctx in ('C1', 'C2', 'C3', 'C4'):
        lines.append('  children Child[]')
    lines += ['  @@index([payload], map: "idx_declared")', f'  @@map("{table}")']
    if (op == 'drop_index' and not after) or (op == 'add_index' and after):
        lines.append('  @@index([value], map: "idx_operation")')
    lines.append('}')
    if ctx in ('C1', 'C2', 'C3', 'C4'):
        action = {'C1': 'Cascade', 'C2': 'SetNull', 'C3': 'Restrict', 'C4': 'Cascade'}[ctx]
        lines += ['model Child {', '  id Int @id', '  parent_id Int?', '  payload String?',
                  f'  parent Parent? @relation(fields: [parent_id], references: [id], onDelete: {action}, onUpdate: NoAction)', '  @@map("children")']
        if ctx == 'C4':
            lines.append('  grandchildren Grandchild[]')
        lines.append('}')
    if ctx == 'C4':
        lines += ['model Grandchild {', '  id Int @id', '  child_id Int?', '  payload String?',
                  '  child Child? @relation(fields: [child_id], references: [id], onDelete: Cascade, onUpdate: NoAction)', '  @@map("grandchildren")', '}']
    if ctx == 'C5':
        lines += ['model Audit {', '  id Int @id', '  parent_id Int?', '  message String?', '  @@map("audit")', '}']
    return '\n'.join(lines) + '\n'
