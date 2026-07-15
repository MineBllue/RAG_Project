# MySQL 性能优化指南

> 来源: 本地生成

# MySQL 性能优化指南

## 1. 索引优化

### 1.1 B+Tree 索引
- 最左前缀原则
- 覆盖索引避免回表
- 避免索引列上使用函数

### 1.2 联合索引
```sql
-- 好的索引设计（考虑查询条件顺序）
CREATE INDEX idx_user_status_time ON orders(user_id, status, create_time);

-- 可以高效执行的查询
SELECT * FROM orders WHERE user_id = 123 AND status = 'active';
SELECT * FROM orders WHERE user_id = 123 AND status = 'active' ORDER BY create_time;
```

### 1.3 索引优化建议
- EXPLAIN 分析执行计划
- type 列从优到差：system > const > eq_ref > ref > range > index > ALL
- rows 列越小越好

## 2. SQL 优化

### 2.1 分页优化
```sql
-- 慢：大偏移量
SELECT * FROM orders ORDER BY id LIMIT 100000, 20;

-- 快：基于主键的延迟关联
SELECT * FROM orders WHERE id >= (SELECT id FROM orders ORDER BY id LIMIT 100000, 1) LIMIT 20;
```

### 2.2 JOIN 优化
- 小表驱动大表
- 确保 JOIN 字段有索引
- 避免 SELECT *

## 3. 事务与锁

### 3.1 隔离级别
| 级别 | 脏读 | 不可重复读 | 幻读 |
|------|------|----------|------|
| READ UNCOMMITTED | Y | Y | Y |
| READ COMMITTED | N | Y | Y |
| REPEATABLE READ (默认) | N | N | Y（MVCC解决） |
| SERIALIZABLE | N | N | N |

### 3.2 死锁预防
- 固定加锁顺序
- 减少事务粒度
- 使用索引减少锁范围

## 4. 慢查询分析

### 配置
```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;
SET GLOBAL log_queries_not_using_indexes = 'ON';
```

### 分析工具
- mysqldumpslow
- pt-query-digest
- Performance Schema