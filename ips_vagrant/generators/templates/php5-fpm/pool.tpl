[ips]

user = vagrant
group = vagrant

listen = /var/run/php5-fpm.sock
listen.owner = www-data
listen.group = www-data

pm = dynamic
pm.max_children = 8
pm.start_servers = 3
pm.min_spare_servers = 2
pm.max_spare_servers = 4
pm.process_idle_timeout = 60s;
pm.max_requests = 100

pm.status_path = /status
ping.path = /ping
ping.response = pong

;slowlog = log/$pool.log.slow
;request_slowlog_timeout = 0
;request_terminate_timeout = 0

chdir = /srv/http

php_flag[display_errors] = on
php_admin_value[error_log] = /var/log/fpm-php.ips.log
php_admin_flag[log_errors] = on
;php_admin_value[memory_limit] = 32M