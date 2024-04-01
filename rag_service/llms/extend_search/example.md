Q：查询openeuler各版本对应的内核版本
A：
{
    "sql":"SELECT openeuler_version, kernel_version FROM public.kernel_version LIMIT 100;"
}

Q：openeuler有多少个版本
A：
{
    "sql":"SELECT COUNT(DISTINCT openeuler_version) FROM public.kernel_version LIMIT 100;"
}

Q：你好
A：
{
    "sql":""
}