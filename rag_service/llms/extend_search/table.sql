
CREATE TABLE public.kernel_version (
	id bigserial NOT NULL,
	openeuler_version varchar NULL, -- openEuler版本
	kernel_version varchar NULL, -- linux内核版本
	created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP, -- 创建时间
	updated_at timestamp NULL DEFAULT CURRENT_TIMESTAMP, -- 更新时间
	version_type varchar NULL, -- openeuler的社区版本类型，包含社区创新版本、长期支持版本、其他版本
	CONSTRAINT kernel_version_pk PRIMARY KEY (id)
);
COMMENT ON TABLE public.kernel_version IS 'openEuler各版本对应的linux内核版本,openEuler各版本的社区版本类型';

CREATE TABLE public.oe_compatibility_card (
id bigserial NOT NULL,
architecture varchar NULL, -- 架构
board_model varchar NULL, -- 板卡型号
chip_model varchar NULL, -- 板卡名称
chip_vendor varchar NULL, -- 板卡厂家
device_id varchar NULL, --板卡驱动id
download_link varchar NULL, --板卡驱动下载链接
driver_date varchar NULL, --板卡驱动发布日期
driver_name varchar NULL, -- 板卡驱动名称
driver_size varchar NULL, --板卡驱动模块大小
item varchar NULL, 
lang varchar NULL,
openeuler_version varchar NULL, -- openeEuler版本
sha256 varchar NULL,
ss_id varchar NULL,
sv_id varchar NULL,
"type" varchar NULL, -- 类型
vendor_id varchar NULL,
"version" varchar NULL, -- 板卡对应的驱动版本
CONSTRAINT oe_compatibility_card_pkey PRIMARY KEY (id)
);
COMMENT ON TABLE public.oe_compatibility_card IS 'openEuler支持的板卡,用户查询板卡信息时，将用户输入的板卡名称和chip_model进行匹配之后再关联相关信息';

CREATE TABLE public.oe_compatibility_commercial_software (
id bigserial NOT NULL,
data_id varchar NULL,
"type" varchar NULL, -- ISV（独立软件供应商）商业软件类型
test_organization varchar NULL, -- 测试机构
product_name varchar NULL, -- ISV（独立软件供应商）商业软件名称
product_version varchar NULL, -- ISV（独立软件供应商）商业软件版本
company_name varchar NULL, -- ISV（独立软件供应商）名称
platform_type_and_server_model varchar NULL,
authenticate_link varchar NULL,
openeuler_version varchar NULL, -- openEuler版本
region varchar NULL,
CONSTRAINT oe_compatibility_commercial_software_pkey PRIMARY KEY (id)
);
COMMENT ON TABLE public.oe_compatibility_commercial_software IS 'openEuler支持的ISV（独立软件供应商）商业软件，这里面的软件名几乎都是中文的，
并且都是较为上层的服务，例如数牍科技Tusita隐私计算平台、全自动化码头智能生产指挥管控系统、智慧医院运营指挥平台等';

CREATE TABLE public.oe_compatibility_open_source_software (
id bigserial NOT NULL,
openeuler_version varchar NULL, -- openEuler版本
arch varchar NULL, -- ISV（独立软件供应商）开源软件支持的架构
property varchar NULL, -- ISV（独立软件供应商）开源软件属性
result_url varchar NULL,
result_root varchar NULL,
bin varchar NULL,
uninstall varchar NULL,
license varchar NULL, -- ISV（独立软件供应商）开源软件开源协议
libs varchar NULL,
install varchar NULL,
src_location varchar NULL,
"group" varchar NULL,
cmds varchar NULL,
"type" varchar NULL, -- ISV（独立软件供应商）开源软件类型
"softwareName" varchar NULL, -- ISV（独立软件供应商）开源软件软件名称
category varchar NULL,
"version" varchar NULL, --ISV（独立软件供应商）开源软件 版本
"downloadLink" varchar NULL,
CONSTRAINT oe_compatibility_open_source_software_pkey PRIMARY KEY (id)
);
COMMENT ON TABLE public.oe_compatibility_open_source_software IS 'openEuler支持的ISV（独立软件供应商）开源软件，这张表里面只有 tcplay tcpxtract pmount cadaver cycle vile gcx dpdk-tools quagga esound-daemon这些开源软件';

CREATE TABLE public.oe_compatibility_osv (
id varchar NOT NULL,
arch varchar NULL, -- 架构
os_version varchar NULL, -- 商用操作系统版本
osv_name varchar NULL, -- OS厂商
"date" varchar NULL, -- 测评日期
os_download_link varchar NULL, -- OS下载地址
"type" varchar NULL,
details varchar NULL,
friendly_link varchar NULL,
total_result varchar NULL,
checksum varchar NULL,
openeuler_version varchar NULL, -- openEuler版本
CONSTRAINT oe_compatibility_osv_pkey PRIMARY KEY (id)
);
COMMENT ON TABLE public.oe_compatibility_osv IS 'openEuler支持的OSV(Operating System Vendor,操作系统供应商)，例如深圳开鸿数字产业发展有限公司、中科方德软件有限公司等公司基于openEuler的商用版本OSV相关信息都可以从这张表获取';

CREATE TABLE public.oe_compatibility_overall_unit (
id bigserial NOT NULL,
architecture varchar NULL, -- 架构
bios_uefi varchar NULL,
certification_addr varchar NULL,
certification_time varchar NULL,
commitid varchar NULL,
computer_type varchar NULL,
cpu varchar NULL, -- 整机的cpu型号
"date" varchar NULL, -- 日期
friendly_link varchar NULL,
hard_disk_drive varchar NULL,--整机的硬件驱动
hardware_factory varchar NULL, -- 整机的厂家
hardware_model varchar NULL, -- 整机的型号
host_bus_adapter varchar NULL,
lang varchar NULL,
main_board_bodel varchar NULL,
openeuler_version varchar NULL, -- 整机的支持openEuler版本
ports_bus_types varchar NULL, --整机的端口或总线类型
product_information varchar NULL, --整机详细介绍所在的链接
ram varchar NULL, --整机的内存配置
update_time varchar NULL, 
video_adapter varchar NULL, --整机的视频适配器
compatibility_configuration varchar NULL, --整机的兼容性信息
"boardCards" varchar NULL, --整机的板卡
CONSTRAINT oe_compatibility_overall_unit_pkey PRIMARY KEY (id)
);
COMMENT ON TABLE public.oe_compatibility_overall_unit IS 'openEuler各版本支持的整机,对于类似openEuler 20.03 LTS支持哪些整机可以从这张表里进行查询';

CREATE TABLE public.oe_compatibility_solution (
id bigserial NOT NULL,
architecture varchar NULL, -- 架构
bios_uefi varchar NULL,
certification_type varchar NULL, -- 类型
cpu varchar NULL, -- 解决方案对应的cpu类型
"date" varchar NULL, -- 日期
driver varchar NULL, -- 解决方案对应的驱动
hard_disk_drive varchar NULL, -- 解决方案对应的硬盘驱动
introduce_link varchar NULL, -- 解决方案详细介绍所在链接
lang varchar NULL,
libvirt_version varchar NULL,
network_card varchar NULL,-- 解决方案对应的网卡
openeuler_version varchar NULL, -- 解决方案对应的openEuler版本
ovs_version varchar NULL, -- 解决方案的版本号
product varchar NULL, -- 型号
qemu_version varchar NULL, -- 解决方案的qemu虚拟机版本
raid varchar NULL, -- 解决方案支持的raid卡
ram varchar NULL, -- 解决方案支持的ram卡
server_model varchar NULL, -- 解决方案的整机类型
server_vendor varchar NULL, -- 解决方案的厂家
solution varchar NULL, -- 解决方案的类型
stratovirt_version varchar NULL,
CONSTRAINT oe_compatibility_solution_pk PRIMARY KEY (id)
);
COMMENT ON TABLE public.oe_compatibility_solution IS 'openeuler支持的解决方案';

CREATE TABLE public.oe_compatibility_oepkgs (
summary varchar(800) NULL,
repotype varchar(30) NULL, --有openeuler_official和openeuler_compatible两种情况，peneuler_official代表这个软件包的下载源是官方的，openeuler_compatible代表这个软件包的下载源是非官方的
openeuler_version varchar(200) NULL, -- openEuler版本
rpmpackurl varchar(300) NULL, -- 软件包下载链接
srcrpmpackurl varchar(300) NULL, -- 软件包源码下载链接
"name" varchar(100) NULL, -- 软件包名
arch varchar(20) NULL, -- 架构
id varchar(30) NULL,
rpmlicense varchar(600) NULL, -- 软件包许可证
"version" varchar(80) NULL -- 软件包版本
);
COMMENT ON TABLE public.oe_compatibility_oepkgs IS 'openEuler各版本支持的开源软件包名和软件包版本，对于类似gcc,glibc,mysql,redis这种常用开源软件软件包在openEuler上的版本信息可以对这张表进行查询。';

CREATE TABLE oe_community_organization_structure (
    id BIGSERIAL PRIMARY KEY, 
    committee_name TEXT, --所属委员会
    role TEXT, --职位
    name TEXT, --姓名
    personal_message TEXT --个人信息
);

COMMENT ON TABLE oe_community_organization_structure IS 'openEuler社区组织架构信息表，存储了各委员会下人员的职位、姓名和个人信息';
