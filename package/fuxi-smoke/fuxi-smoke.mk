################################################################################
#
# fuxi-smoke
#
################################################################################

FUXI_SMOKE_VERSION = 1
FUXI_SMOKE_SITE = $(BR2_EXTERNAL_FUXI_PATH)/package/fuxi-smoke/src
FUXI_SMOKE_SITE_METHOD = local
FUXI_SMOKE_LICENSE = MIT

define FUXI_SMOKE_BUILD_CMDS
	$(TARGET_CC) $(TARGET_CFLAGS) -Wall -Wextra -Werror $(TARGET_LDFLAGS) \
		-o $(@D)/fuxi-smoke $(@D)/fuxi-smoke.c
endef

define FUXI_SMOKE_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/fuxi-smoke $(TARGET_DIR)/usr/bin/fuxi-smoke
endef

$(eval $(generic-package))
