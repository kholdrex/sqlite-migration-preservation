class PilotChange < ActiveRecord::Migration[8.0]
  def change
    add_index :parents, :tenant_id, name: :idx_parents_tenant
  end
end
