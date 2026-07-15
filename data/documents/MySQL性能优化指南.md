# MySQL性能优化指南

# MySQL 性能优化指南
## B+Tree 索引原理
最左前缀原则：联合索引 (a,b,c) 可高效支持 a / a,b / a,b,c 查询，但无法单独索引 b 或 c。
## 慢查询优化
开启 slow_query_log，long_query_time=1s。用 pt-query-digest 分析，关注 rows_examined 过大的查询。
## 事务隔离级别
READ COMMITTED 避免脏读，REPEATABLE READ (默认) 通过 MVCC 避免不可重复读。SERIALIZABLE 最强但性能最差。
## 分库分表
垂直拆分按业务模块，水平拆分按用户ID取模。ShardingSphere 实现透明分片路由。