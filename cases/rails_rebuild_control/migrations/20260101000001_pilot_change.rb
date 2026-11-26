class PilotChange < ActiveRecord::Migration[8.0]
  def change
    change_column_default :parents, :name, from: 'a', to: 'b'
  end
end
