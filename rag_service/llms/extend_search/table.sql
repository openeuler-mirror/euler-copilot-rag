CREATE TABLE public.software_version (
	id bigserial NOT NULL,
	openeuler_version varchar NULL, -- openEuler版本
	openeuler_architecture varchar NULL, -- 架构
	software_name varchar NULL, -- 软件名
	software_version varchar NULL, -- 软件版本
	CONSTRAINT software_version_pk PRIMARY KEY (id)
);
COMMENT ON TABLE public.software_version IS 'openEuler各版本支持的软件名和软件版本';

CREATE TABLE public.kernel_version (
	id bigserial NOT NULL,
	openeuler_version varchar NULL, -- openEuler版本
	kernel_version varchar NULL, -- linux内核版本
	CONSTRAINT kernel_version_pk PRIMARY KEY (id)
);
COMMENT ON TABLE public.kernel_version IS 'openEuler各版本对应的linux内核版本';

CREATE TABLE public.oe_compatibility_card (
	id bigserial NOT NULL,
	architecture varchar NULL, -- 架构
	board_model varchar NULL, -- 板卡型号
	chip_model varchar NULL, -- 芯片型号
	chip_vendor varchar NULL, -- 芯片厂家
	device_id varchar NULL,
	download_link varchar NULL,
	driver_date varchar NULL,
	driver_name varchar NULL, -- 驱动名称
	driver_size varchar NULL,
	item varchar NULL,
	lang varchar NULL,
	os varchar NULL, -- openeEuler版本
	sha256 varchar NULL,
	ss_id varchar NULL,
	sv_id varchar NULL,
	"type" varchar NULL, -- 类型
	vendor_id varchar NULL,
	"version" varchar NULL, -- 版本
	CONSTRAINT oe_compatibility_card_pkey PRIMARY KEY (id)
);
COMMENT ON TABLE public.oe_compatibility_card IS 'openEuler支持的板卡';

CREATE TABLE public.oe_compatibility_commercial_software (
	id bigserial NOT NULL,
	data_id varchar NULL,
	"type" varchar NULL, -- 软件类型
	test_organization varchar NULL, -- 测试机构
	product_name varchar NULL, -- 软件名称
	product_version varchar NULL, -- 软件版本
	company_name varchar NULL, -- 厂家名称
	platform_type_and_server_model varchar NULL,
	authenticate_link varchar NULL,
	os_version varchar NULL, -- openEuler版本
	region varchar NULL,
	CONSTRAINT oe_compatibility_commercial_software_pkey PRIMARY KEY (id)
);
COMMENT ON TABLE public.oe_compatibility_commercial_software IS 'openEuler支持的商业软件';

CREATE TABLE public.oe_compatibility_open_source_software (
	id bigserial NOT NULL,
	os varchar NULL, -- openEuler版本
	arch varchar NULL, -- 架构
	property varchar NULL, -- 软件属性
	result_url varchar NULL,
	result_root varchar NULL,
	bin varchar NULL,
	uninstall varchar NULL,
	license varchar NULL, -- 开源协议
	libs varchar NULL,
	install varchar NULL,
	src_location varchar NULL,
	"group" varchar NULL,
	cmds varchar NULL,
	"type" varchar NULL, -- 软件类型
	"softwareName" varchar NULL, -- 软件名称
	category varchar NULL,
	"version" varchar NULL, -- 版本
	"downloadLink" varchar NULL,
	CONSTRAINT oe_compatibility_open_source_software_pkey PRIMARY KEY (id)
);
COMMENT ON TABLE public.oe_compatibility_open_source_software IS 'openEuler支持的开源软件';

CREATE TABLE public.oe_compatibility_osv (
	id varchar NOT NULL,
	arch varchar NULL, -- 架构
	os_version varchar NULL, -- OS版本
	osv_name varchar NULL, -- OS厂商
	"date" varchar NULL, -- 测评日期
	os_download_link varchar NULL, -- OS下载地址
	"type" varchar NULL,
	details varchar NULL,
	friendly_link varchar NULL,
	total_result varchar NULL,
	checksum varchar NULL,
	base_openeuler_version varchar NULL, -- openEuler版本
	CONSTRAINT oe_compatibility_osv_pkey PRIMARY KEY (id)
);
COMMENT ON TABLE public.oe_compatibility_osv IS 'openEuler支持的OSV';

CREATE TABLE public.oe_compatibility_overall_unit (
	id bigserial NOT NULL,
	architecture varchar NULL, -- 架构
	bios_uefi varchar NULL,
	certification_addr varchar NULL,
	certification_time varchar NULL,
	commitid varchar NULL,
	computer_type varchar NULL,
	cpu varchar NULL, -- CPU
	"date" varchar NULL, -- 日期
	friendly_link varchar NULL,
	hard_disk_drive varchar NULL,
	hardware_factory varchar NULL, -- 硬件厂家
	hardware_model varchar NULL, -- 硬件型号
	host_bus_adapter varchar NULL,
	lang varchar NULL,
	main_board_bodel varchar NULL,
	os_version varchar NULL, -- openEuler版本
	ports_bus_types varchar NULL,
	product_information varchar NULL,
	ram varchar NULL,
	update_time varchar NULL,
	video_adapter varchar NULL,
	compatibility_configuration varchar NULL,
	"boardCards" varchar NULL,
	CONSTRAINT oe_compatibility_overall_unit_pkey PRIMARY KEY (id)
);
COMMENT ON TABLE public.oe_compatibility_overall_unit IS 'openEuler支持的整机';

CREATE TABLE public.oe_compatibility_solution (
	id bigserial NOT NULL,
	architecture varchar NULL, -- 架构
	bios_uefi varchar NULL,
	certification_type varchar NULL, -- 类型
	cpu varchar NULL,
	"date" varchar NULL, -- 日期
	driver varchar NULL,
	hard_disk_drive varchar NULL,
	introduce_link varchar NULL,
	lang varchar NULL,
	libvirt_version varchar NULL,
	network_card varchar NULL,
	os varchar NULL, -- openEuler版本
	ovs_version varchar NULL,
	product varchar NULL, -- 型号
	qemu_version varchar NULL,
	raid varchar NULL,
	ram varchar NULL,
	server_model varchar NULL,
	server_vendor varchar NULL, -- 厂家
	solution varchar NULL, -- 解决方案
	stratovirt_version varchar NULL,
	CONSTRAINT oe_compatibility_solution_pk PRIMARY KEY (id)
);
COMMENT ON TABLE public.oe_compatibility_solution IS 'openeuler支持的解决方案';