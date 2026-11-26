class PilotChange < ActiveRecord::Migration[8.0]
  def change
    add_foreign_key :parents, :tenants, column: :tenant_id
  end
end
