class PilotChange < ActiveRecord::Migration[8.0]
  def change
    add_column :parents, :note, :text
  end
end
