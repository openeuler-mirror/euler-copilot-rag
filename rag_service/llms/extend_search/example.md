Q：查询openeuler各版本对应的内核版本
A：
{
    "sql":"SELECT DISTINCT openeuler_version, kernel_version FROM public.kernel_version LIMIT 30;"
}

Q：openeuler有多少个版本
A：
{
    "sql":"SELECT DISTINCT COUNT(DISTINCT openeuler_version) FROM public.kernel_version LIMIT 30;"
}

Q：OSV中，操作系统1060e基于什么openeuler版本
A：
{
    "sql":"SELECT DISTINCT openeuler_version FROM public.oe_compatibility_osv WHERE os_version ILIKE '%1060e%' LIMIT 30"
}

Q：你好
A：
{
    "sql":""
}