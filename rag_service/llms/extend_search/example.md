Q：查询openeuler各版本对应的内核版本
A：SELECT DISTINCT openeuler_version, kernel_version FROM public.kernel_version LIMIT 30

Q：openeuler有多少个版本
A：SELECT DISTINCT COUNT(DISTINCT openeuler_version) FROM public.kernel_version LIMIT 30

Q：openEuler社区创新版本有哪些？
A：SELECT DISTINCT openeuler_version FROM kernel_version where version_type ilike '%社区创新版本%';

Q：openEuler有哪些版本？
A：SELECT DISTINCT openeuler_version FROM kernel_version;

Q：openEuler社区长期支持版本有哪些？
A：SELECT DISTINCT openeuler_version FROM kernel_version where version_type= '长期支持版本';

Q：OSV中，操作系统1060e基于什么openeuler版本
A：SELECT DISTINCT openeuler_version FROM public.oe_compatibility_osv WHERE os_version ILIKE '1060e' LIMIT 30

Q：查询openEuler对应gcc对应版本
A：select DISTINCT openeuler_version,name,version  from oe_compatibility_oepkgs  where name ILIKE 'gcc';

Q：请以表格的形式列出openEuler与gcc对应关系
A：select DISTINCT openeuler_version,name,version  from oe_compatibility_oepkgs  where name ILIKE 'gcc';

Q：查询openEuler-20.09对应glibc对应版本
A：select DISTINCT openeuler_version,name,version  from oe_compatibility_oepkgs  where openeuler_version ILIKE '%openEuler-20.09%' and name ILIKE 'glibc';

Q：查询openEuler-20.09对应gcc对应版本
A：select DISTINCT openeuler_version,name,version  from oe_compatibility_oepkgs  where openeuler_version ILIKE '%openEuler-20.09%' and name ILIKE 'gcc';

Q：查询openEuler-20.09对应glibc下载链接
A：select concat('openEuler-20.09对应glibc下载链接为',rpmpackurl)  from oe_compatibility_oepkgs  where openeuler_version ILIKE '%openEuler-20.09%' and name ILIKE'glibc';

Q：openEuler-20.03的gcc下载是什么
A：select concat('openEuler-20.03对应gcc下载链接为',rpmpackurl)  from oe_compatibility_oepkgs  where openeuler_version ILIKE '%openEuler-20.03%' and name ILIKE 'gcc';

Q：查询openEuler 20.03 LTS支持哪些整机，列出它们的硬件型号、硬件厂家、架构
A：select hardware_model,hardware_factory,architecture from oe_compatibility_overall_unit where openeuler_version ILIKE 'openEuler-20.03-LTS-SP3';

Q：深圳开鸿数字产业发展有限公司基于openEuler的什么版本发行了什么商用版本，请列出商用操作系统版本、openEuler操作系统版本以及下载地址
A：select os_version,openeuler_version,os_download_link from oe_compatibility_osv where osv_name ILIKE'深圳开鸿数字产业发展有限公司';

Q：udp720的板卡型号是多少？
A：SELECT DISTINCT chip_model,board_model FROM oe_compatibility_card WHERE chip_model ILIKE 'upd720';

Q：请列举openEuler的10个isv软件？
A：SELECT product_name, product_version, company_name,openeuler_version FROM oe_compatibility_commercial_software LIMIT 10;

Q：openEuler 20.03 LTS支持哪些板卡？
A：SELECT DISTINCT chip_model FROM oe_compatibility_card where openeuler_version ILIKE '%openEuler-20.03-LTS%';

Q：openEuler 20.03 LTS支持哪些芯片？
A：SELECT DISTINCT chip_model FROM oe_compatibility_card where openeuler_version ILIKE '%openEuler-20.03-LTS%';

Q：openEuler专家委员会委员有哪些？
A：SELECT DISTINCT name FROM oe_community_organization_structure WHERE committee_name ILIKE '%专家委员会%';

Q：openEuler品牌委员会主席是谁？
A：SELECT DISTINCT name FROM oe_community_organization_structure WHERE committee_name ILIKE '%品牌委员会%' AND ROLE ILIKE '%主席%';

表中带双引号的变量在查的时候也得带上双引号下面是一个例子：
Q：查询一个openEuler的ISV软件名
A：SELECT "softwareName" FROM oe_compatibility_open_source_software LIMIT 1;