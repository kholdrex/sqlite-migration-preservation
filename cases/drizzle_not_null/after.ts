import { sqliteTable, integer, text, index } from 'drizzle-orm/sqlite-core';
export const tenants = sqliteTable('tenants', {
  id: integer('id').primaryKey(), name: text('name').notNull(),
});
export const parents = sqliteTable('parents', {
  id: integer('id').primaryKey(), tenantId: integer('tenant_id'),
  name: text('name').default('a').notNull(),
}, table => [index('idx_parents_name').on(table.name)]);
export const children = sqliteTable('children', {
  id: integer('id').primaryKey(),
  parentId: integer('parent_id').notNull().references(() => parents.id, { onDelete: 'cascade' }),
  payload: text('payload').notNull(),
}, table => [index('idx_children_parent').on(table.parentId)]);
export const audit = sqliteTable('audit', {
  id: integer('id').primaryKey(), message: text('message').notNull(),
});
