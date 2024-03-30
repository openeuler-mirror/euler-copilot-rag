Q：查询openeuler各版本对应的内核版本
A：
{
    "sql":"SELECT openeuler_version, kernel_version FROM public.kernel_version LIMIT 30;"
}
Q：查询openeuler2203lts的nginx版本
A：
{
    "sql":"SELECT software_version FROM public.software_version WHERE openeuler_version = 'openEuler-22.03-LTS' AND software_name = 'nginx' LIMIT 30;"
}