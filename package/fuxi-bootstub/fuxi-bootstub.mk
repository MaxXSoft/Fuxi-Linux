################################################################################
#
# fuxi-bootstub
#
################################################################################

FUXI_BOOTSTUB_VERSION = 1
FUXI_BOOTSTUB_SITE = $(BR2_EXTERNAL_FUXI_PATH)/package/fuxi-bootstub/src
FUXI_BOOTSTUB_SITE_METHOD = local
FUXI_BOOTSTUB_LICENSE = MIT
FUXI_BOOTSTUB_INSTALL_IMAGES = YES
FUXI_BOOTSTUB_INSTALL_TARGET = NO

define FUXI_BOOTSTUB_BUILD_CMDS
	$(TARGET_CC) -march=rv32i_zicsr -mabi=ilp32 -nostdlib -nostartfiles \
		-static -Wl,--build-id=none -Wl,--no-relax -Wl,-T,$(@D)/link.ld \
		-o $(@D)/fuxi-bootstub.elf $(@D)/boot.S
	$(TARGET_OBJCOPY) -O binary $(@D)/fuxi-bootstub.elf $(@D)/fuxi-bootstub.bin
endef

define FUXI_BOOTSTUB_INSTALL_IMAGES_CMDS
	$(INSTALL) -m 0644 $(@D)/fuxi-bootstub.elf $(BINARIES_DIR)/fuxi-bootstub.elf
	$(INSTALL) -m 0644 $(@D)/fuxi-bootstub.bin $(BINARIES_DIR)/fuxi-bootstub.bin
endef

$(eval $(generic-package))
