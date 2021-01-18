#!/usr/bin/python3
#
#

cardid = 0
hprefix = "      "
osicons = {
    "Debian": "debian",
    "Ubuntu": "ubuntu",
    "RedHat": "hat-fedora",
    "FreeBSD": "freebsd",
    "OpenBSD": "openbsd",
    "NetBSD": "netbsd",
    "Suse": "opensuse",
    "LibreELEC": "youtube-tv",
    "OpenWrt": "router-wireless",
    "Windows": "windows",
    "Darwin": "apple",
    "OmniOS": "omnios",
}


def osicons_get(osfamily, distribution=""):
    if osfamily in osicons:
        return osicons[osfamily]
    elif distribution in osicons:
        return osicons[distribution]
    else:
        return "monitor"


def bs_card_begin(title="", icon="", collapse=False):
    global hprefix
    global cardid
    classes = ""
    toggle = ""
    if collapse == True:
        classes = "collapse"
    html = ""
    html += hprefix + "<div class='card'>\n"
    if icon != "":
        html += (
            hprefix
            + " <div class='card-header' data-toggle='"
            + classes
            + "' data-target='#cid"
            + str(cardid)
            + "'>"
            + title
            + "<img class='float-right' src='assets/MaterialDesignIcons/"
            + icon
            + ".svg'></div>\n"
        )
    elif title != "":
        html += (
            hprefix
            + " <div class='card-header' data-toggle='"
            + classes
            + "' data-target='#cid"
            + str(cardid)
            + "'>"
            + title
            + "</div>\n"
        )
    html += (
        hprefix
        + " <div id='cid"
        + str(cardid)
        + "' class='card-body "
        + classes
        + "'>\n"
    )
    hprefix += " "
    hprefix += " "
    cardid += 1
    return html


def bs_card_end():
    global hprefix
    hprefix = hprefix[:-1]
    hprefix = hprefix[:-1]
    html = hprefix + "</div></div><!--/card-->\n"
    return html


def bs_row_begin():
    global hprefix
    html = hprefix + "<div class='row'>\n"
    hprefix += " "
    return html


def bs_row_end():
    global hprefix
    hprefix = hprefix[:-1]
    html = hprefix + "</div><!--/row-->\n"
    return html


def bs_col_begin(width):
    global hprefix
    html = hprefix + "<div class='col-" + width + "'>\n"
    hprefix += " "
    return html


def bs_col_end():
    global hprefix
    hprefix = hprefix[:-1]
    html = hprefix + "</div><!--/col-->\n"
    return html


def bs_table_begin():
    global hprefix
    html = hprefix + "<table>\n"
    hprefix += " "
    return html


def bs_table_end():
    global hprefix
    hprefix = hprefix[:-1]
    html = hprefix + "</table>\n"
    return html


def bs_add(html):
    global hprefix
    html = hprefix + html + "\n"
    return html
