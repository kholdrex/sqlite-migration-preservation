require "active_record"
require "sqlite3"
require "json"
require "logger"
require "digest"

schema_path, migration_dir, output_dir = ARGV
ActiveRecord::Base.establish_connection(adapter: "sqlite3", database: schema_path)
ActiveRecord::Base.logger = Logger.new(File.join(output_dir, "active_record.log"))
connection = ActiveRecord::Base.connection
connection.execute("PRAGMA foreign_keys = ON")
metadata = {
  ruby: RUBY_VERSION,
  activerecord: ActiveRecord::VERSION::STRING,
  sqlite3_gem: SQLite3::VERSION,
  sqlite: connection.select_value("SELECT sqlite_version()"),
  foreign_keys_before: connection.select_value("PRAGMA foreign_keys"),
  gems: Gem.loaded_specs.transform_values { |spec| spec.version.to_s }
}
source = Bundler.load.specs.find { |spec| spec.name == "activerecord" }.source
if source.respond_to?(:revision)
  adapter = connection.method(:alter_table).source_location.first
  metadata[:activerecord_revision] = source.revision
  metadata[:adapter_sha256] = Digest::SHA256.file(adapter).hexdigest
  metadata[:adapter_source] = adapter
end
statements = []
subscription = ActiveSupport::Notifications.subscribe("sql.active_record") do |*, payload|
  statements << {sql: payload[:sql], name: payload[:name], exception: payload[:exception]}
end
begin
  context = ActiveRecord::MigrationContext.new(migration_dir)
  context.migrate
  metadata[:success] = true
rescue StandardError => error
  metadata[:success] = false
  metadata[:error] = "#{error.class}: #{error.message}"
ensure
  ActiveSupport::Notifications.unsubscribe(subscription)
  metadata[:foreign_keys_after] = connection.select_value("PRAGMA foreign_keys")
  File.write(File.join(output_dir, "events.json"), JSON.pretty_generate(statements))
  File.write(File.join(output_dir, "executed.sql"), statements.map { |e| e[:sql].sub(/;\s*\z/, "") + ";\n" }.join)
  File.write(File.join(output_dir, "runner.json"), JSON.pretty_generate(metadata))
  ActiveRecord::Base.connection_pool.disconnect!
end
exit(metadata[:success] ? 0 : 1)
