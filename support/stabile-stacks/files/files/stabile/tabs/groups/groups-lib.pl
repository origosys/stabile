#!/usr/bin/perl

use MIME::Base64 qw( decode_base64 );

@groupprops = ("description", "member");

sub groups {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    unless ($action eq 'restore' || $sambadomain) {
        my $intip = `cat /tmp/internalip`;
        $intip = `cat /etc/origo/internalip` if (-e '/etc/origo/internalip');
        my $dominfo = `samba-tool domain info $intip`;
        $sambadomain = $1 if ($dominfo =~ /Domain\s+: (\S+)/);
    }
    unless ($action eq 'restore' || $userbase) {
        my @domparts = split(/\./, $sambadomain);
        $userbase = "CN=users,DC=" . join(",DC=", @domparts);
    }

    if ($action eq 'form') {
# Generate and return the HTML form for this tab
        my $form = <<END
<div class="tab-pane" id="groups">
    <div style="width:100%; height:310px; overflow-y:scroll;">
      <table class="table table-condensed table-striped small" id="groups_table" style="width: 100%; border:none;">
        <thead>
          <tr>
            <th>Name</th>
            <th>Description</th>
            <th>Members</th>
            <th>DN</th>
          </tr>
        </thead>
        <tbody>
        </tbody>
      </table>
    </div>
    <div style="margin-top:6px; padding-top:4px ; border-top:2px solid #DDDDDD">
        <button class="btn btn-default" id="update_groups" title="Click to check refresh group list." rel="tooltip" data-placement="top" onclick="\$('[rel=tooltip]').tooltip('hide'); updateSambaGroups(); return false;"><span class="glyphicon glyphicon-repeat" id="urglyph"></button>
        <button class="btn btn-default" id="new_group" title="Click to add a group." rel="tooltip" data-placement="top" onclick="\$('[rel=tooltip]').tooltip('hide'); editSambaGroup(); return false;">New group</button>
    </div>
</div>

<div class="modal" id="editGroupDialog" tabindex="-1" role="dialog" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-body">
        <h4 class="modal-title" id="group_label">Edit group</h4>
        <form id="edit_group_form" class="small" method="post" action="index.cgi?action=savesambagroup\&tab=groups" autocomplete="off">
            <table width="100\%" style="padding:2px;">
                <tr>
                    <td width="200">Name:</td><td class="passwordform"><input readonly type="text" name="editgroup_cn" id="editgroup_cn" /></td>
                </tr>
                <tr>
                    <td width="200">Description:</td><td class="passwordform"><input type="text" name="editgroup_description" id="editgroup_description" /></td>
                </tr>
                <tr>
                    <td width="200">Members (1 per line):</td><td class="passwordform"><textarea class="field" name="editgroup_member" id="editgroup_member"></textarea></td>
                </tr>
                <tr>
                    <td width="200" valign="top">Write list (comma separated):</td><td class="passwordform">
                        <input type="text" name="editgroup_writelist" id="editgroup_writelist" />
                        <span style="float: left; font-size: 13px;">leave empty to allow all members write access.</span>
                    </td>
                </tr>
            </table>
            <input type="hidden" name="editgroup_dn" id="editgroup_dn" />
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-default pull-left" data-dismiss="modal" onclick="confirmGroupAction('delete', \$('#editgroup_cn').val());">Delete</button>
        <button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-primary" onclick="saveSambaGroup(\$('#editgroup_cn').val());">Save</button>
      </div>
    </div>
  </div>
</div>
END
;
        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs

        my $js = <<END
    \$(document).ready(function () {
        sambaGroupsTable = \$('#groups_table').DataTable({
            searching: false,
            paging: false,
            columns: [
                { data: "cn" },
                { data: "description" },
                { data: "member" },
                { data: "dn" }
            ],
            columnDefs: [
                {
                    targets: [ 0 ],
                    render: function ( data, type, row ) {
                                    return ('<a href="#" onclick="editSambaGroup(\\''+ data + '\\');">' + data +'</a>');
                                }
                },
                {
                    targets: [ 2 ],
                    visible: false,
                },
                {
                    targets: [ 3 ],
                    visible: false,
                    searchable: false
                }
            ],
            ajax: {
                url: "index.cgi?tab=groups\&action=listsambagroups",
                dataSrc: ""
            }
        });
    });

    function updateSambaGroups() {
        \$('#update_groups').prop( "disabled", true);
        \$('#urglyph').attr('class','glyphicon glyphicon-refresh');
        sambaGroupsTable.ajax.reload(function ( json ) {
                                        \$('#update_groups').prop( "disabled", false);
                                        \$('#urglyph').attr('class','glyphicon glyphicon-repeat');
                                    });
    }

    function editSambaGroup(cn) {
        var editrow = [];
        if (cn) {
            \$('#editgroup_cn').val(cn);
            \$('#editgroup_cn').prop("readonly",true);
            \$.each(sambaGroupsTable.data(), function(index, irow) {
                if (irow["cn"] == cn) editrow = irow;
            });
            if(editrow) {
                \$('#editgroup_dn').val(editrow["dn"]);
                \$('#editgroup_description').val(editrow["description"]);
                \$('#editgroup_member').val(editrow["member"]);
                \$('#editgroup_writelist').val(editrow["writelist"]);
            }
            \$('#group_label').html("Edit group");
            \$('#editgroup_member').prop( "disabled", false);
        } else {
        // New group
            \$('#editgroup_dn').val("new");
            \$('#editgroup_cn').val('');
            \$('#editgroup_cn').prop("readonly",false);
            \$('#editgroup_member').val('');
            \$('#editgroup_description').val('');
            \$('#group_label').html("New group");
            \$('#editgroup_member').prop( "disabled", true);
            \$('#editgroup_writelist').val('');
        }
        \$('#editGroupDialog').modal({'backdrop': false, 'show': true});
        \$('#editgroup_cn').focus();
    }

    function saveSambaGroup(cn) {
        var editrow = [];
        console.log("Saving group", cn);
        var userrow = [];

        \$.each(sambaUsersTable.data(), function(index, irow) {
            if (irow["cn"] == cn) userrow = irow;
        });

        if (userrow.length==0) {
            \$.each(sambaGroupsTable.data(), function(index, irow) {
                if (irow["cn"] == cn) editrow = irow;
            });

            \$.each(editrow, function( prop, oldval ) {
                var newval = \$("#editgroup_" + prop).val();
                if (!newval && oldval) \$("#editgroup_" + prop).val("--");
            });

            \$.post( "index.cgi?action=savesambagroup\&tab=groups", \$("#edit_group_form").serialize())
            .done(function( data ) {
                salert(data);
                updateSambaGroups();
            })
            .fail(function() {
                salert( "An error occurred :(" );
            });
        } else {
            salert("Please use a group name which is not used as a user name also!");
        }


        \$('#editGroupDialog').modal('hide');
        return(false);
    }

    function deleteSambaGroup() {
        var editrow = [];
        console.log("Deleting group", \$("#editgroup_cn").val());

        \$.post( "index.cgi?action=deletesambagroup&tab=groups", \$("#edit_group_form").serialize())
        .done(function( data ) {
            salert(data);
            updateSambaGroups();
        })
        .fail(function() {
            salert( "An error occurred :(" );
        });

        \$('#editGroupDialog').modal('hide');
        return(false);
    }

    function confirmGroupAction(action, cn) {
        if (action == 'delete') {
            \$('#confirmdialog').prop('actionform', "deleteSambaGroup");
            \$('#confirmdialog').modal({'backdrop': false, 'show': true});
            return false;
        }
    };


END
;
        return $js;

    } elsif ($action eq 'deletesambagroup' && defined $in{editgroup_cn}) {
        my $res = "Content-type: text/html\n\n";
        my $groupname = $in{editgroup_cn};
        if ($sysgroups{lc $groupname}) {
            $res .= "Please do not delete system groups";
        } else {
            my $cmd = qq[samba-tool group delete "$groupname"];
            $cmdres .= `$cmd`;
            if ($cmdres =~ /Deleted/) {
                $res .= "Group deleted: $cmdres";
                # Also remove group share
                unlink("/etc/samba/smb.conf.group.$groupname");
                `perl -ni -e 'print unless (/$groupname/)' /etc/samba/smb.conf.groups`;
                `service samba4 restart`;
                # Check if share dir is empty, and if not, archive it
                # Note that this does not check for ".files"
                # See: http://stackoverflow.com/questions/4493482/detect-empty-directory-with-perl
                my $dir = "/mnt/data/groups/$groupname";
                if (scalar <"$dir/*">) {
                    unless (-d "/mnt/data/archive") {
                        `mkdir -p /mnt/data/archive`;
                        `ln -s /mnt/data/archive /mnt/data/users/administrator/`;
                    }
                    my $datestr = localtime() . '';
                    `mv "/mnt/data/groups/$groupname" "/mnt/data/user/archive/$groupname ($datestr)"`;
                    $res .= " Group share not empty - archived. ";
                } else {
                    `rm -r "/mnt/data/groups/$groupname"` if ($groupname);
                }
            } else {
                $res .= "Group not deleted - there was a problem ($cmd, $cmdres)";
            }
        }
        return $res;

    } elsif ($action eq 'savesambagroup' && defined $in{editgroup_dn}) {
        my $res = "Content-type: text/html\n\n";
        my $cmd;
        my $cmdres;
        my $cmdalert;
        my $writelist = '\n    read only = no';
        my $groupname = $in{editgroup_cn};
        if ($in{editgroup_writelist} && $in{editgroup_writelist} ne '--') { # Limit write access to group
            my @garray = split(/\n/, `samba-tool group list`);
            my %ghash = map { lc $_ => $_ } @garray; # Create hash with all groups
            my @writers = split(/, ?/, $in{editgroup_writelist});
            my $writel;
            foreach my $writer (@writers) {
                my $plus = '';
                $plus = '+' if ($ghash{lc $writer});
                $writel .= qq|$plus\\"$sambadomain\\\\$writer\\" |;
            }
            $writelist = <<END

    write list = $writel
    read only = yes
END
;
            chomp $writelist;
        }
        if ($in{editgroup_dn} eq 'new') {
            if ($userbase && $groupname) {
                $cmd = qq[samba-tool group add "$groupname"];
                $cmd .= qq[ --description "$in{editgroup_description}"] if ($in{editgroup_description});
                $cmdres .= `$cmd 2>\&1`;
                if ($cmdres =~ /^Added group/) {
                    # Also add group share
                    `/bin/mkdir -p "/mnt/data/groups/$groupname"`;
                    `/bin/chmod 777 "/mnt/data/groups/$groupname"`;
                    my $validusers = '+\"' . $sambadomain . '\\\\\\' . $groupname . '\"';
                    $txt = <<END
[$groupname]
    path = /mnt/data/groups/$groupname
    browseable = no
    hide dot files = yes
    hide unreadable = yes
    create mode = 0660
    directory mode = 0770
    inherit acls = Yes
    valid users = $validusers
END
;
                    `echo "$txt" > "/etc/samba/smb.conf.group.$groupname"`;
                    `perl -pi -e 's/\\[$groupname\\]/[$groupname]$writelist/;' "/etc/samba/smb.conf.group.$groupname"`;
                    `echo "include = /etc/samba/smb.conf.group.$groupname" >> /etc/samba/smb.conf.groups` unless (`grep "smb.conf.group.$groupname" /etc/samba/smb.conf.groups`);
                    `service samba4 restart`;
                } else {
                    $cmdalert .= "there was a problem: $cmdres";
                }
            } else {
                $cmdalert .= "no userbase" if (!$userbase);
                $cmdalert .= "Please provide a user name" if (!$groupname);
            }
        } else {
            my $laction;
            $laction .= "changetype: modify\n";
            my $changes;
            foreach my $prop (@groupprops) {
                if ($prop eq 'member') {
                    opendir(my $dh, "/mnt/data/groups/$groupname") || die "can't opendir: $!";
                    while(readdir $dh) {
                        unlink("/mnt/data/groups/$groupname/" . $_) if ($_ =~ /^\.groupaccess_/);
                    }
                    closedir $dh;
                }
                if ($in{"editgroup_$prop"} eq '--') {
                    $laction .= "delete: $prop\n";
                    $laction .= "-\n";
                    $changes = 1;
                } elsif ($in{"editgroup_$prop"}) {
                    $changes = 1;
                    if ($prop eq 'member') {
                        my @garray = split(/\n/, `samba-tool group list`);
                        my %ghash = map { lc $_ => $_ } @garray; # Create hash with all groups

                        $laction .= "delete: $prop\n"; # First delete all current members
                        $laction .= "-\n";
                        my @members = split(/\n/, $in{"editgroup_$prop"});
                        foreach my $mem (@members) { # Add members
                            chomp $mem;
                            $mem =~ s/\r//;
                            next unless ($mem);
                            $laction .= "add: $prop\n";
                            $laction .= "$prop: CN=$mem,$userbase\n";
                            $laction .= "-\n";
                            my @mems = ($mem);
                            # Touch file which gives group access for browsing through Apache
                            # We use a custom access control scheme which uses mod_rewrite
                            # If we are dealing with a group include all members
                            @mems = split(/\n/, `samba-tool group listmembers "$mem"`) if ($ghash{lc $mem});
                            foreach my $memb (@mems) {
                                my $groupaccess = "/mnt/data/groups/$groupname/.groupaccess_" . lc $memb;
                                `touch "$groupaccess"` unless (-e $groupaccess);
                            }
                        }
                    } else {
                        $laction .= "replace: $prop\n";
                        $laction .= "$prop: ". $in{"editgroup_$prop"} . "\n";
                        $laction .= "-\n";
                    }
                }
            };

            my $ldif = <<END
dn: $in{editgroup_dn}
$laction
END
;
            $cmd = qq[echo "$ldif"| ldbmodify -H /opt/samba4/private/sam.ldb --] if ($changes);
            $cmdres .= `$cmd 2>\&1` if ($cmd);

            if (defined $in{editgroup_writelist} && !$sysgroups{lc $groupname}) { # Limit write access to shared
                `perl -ni -e 'print unless (/write list/)' "/etc/samba/smb.conf.group.$groupname"`;
                `perl -ni -e 'print unless (/read only/)' "/etc/samba/smb.conf.group.$groupname"`;
                `perl -pi -e 's/\\[$groupname\\]/[$groupname]$writelist/;' "/etc/samba/smb.conf.group.$groupname"`;
                `/etc/init.d/samba4 restart`;
            }

        }

        if ($cmdalert) {
            $res .= $cmdalert;
        } elsif (!$cmd) {
            $res .= "Group updated";
        } elsif ($cmdres =~ /Added group/ || $cmdres =~ /success/) {
            $res .= "Group saved: $cmdres";
        } else {
            $cmdres =~ s/\n/ /;
            $cmdres = $1 if ($cmdres =~ /ERR: \(.*\) "(.+)"/);
            $res .= "Group not saved ($cmdres)";
            $cmd =~ s/"/\\"/;
            `echo "$cmdres" >> /tmp/ldbmodify.out`;
        }
        return $res;

    } elsif ($action eq 'listsambagroups') {
        my %sambagroups = getGroups();
        my $res = "Content-type: application/json\n\n";
        my @uarray = values %sambagroups;
        my $ujson = to_json(\@uarray, {pretty=>1});
        $res  .= $ujson;
        return $res;

    } elsif ($action eq 'upgrade') {

# This is called from origo-ubuntu.pl when rebooting and with status "upgrading"
    } elsif ($action eq 'restore') {

    }

}

sub getGroups {
    unless ($sambadomain) {
        my $intip = `cat /tmp/internalip`;
        $intip = `cat /etc/origo/internalip` if (-e '/etc/origo/internalip');
        my $dominfo = `samba-tool domain info $intip`;
        $sambadomain = $1 if ($dominfo =~ /Domain\s+: (\S+)/);
    }
    unless ($userbase) {
        my @domparts = split(/\./, $sambadomain);
        $userbase = "CN=users,DC=" . join(",DC=", @domparts);
    }

    my %groups;
    my $fields = join(" ", @groupprops) . '';
    my $groups_text = `ldbsearch -H /opt/samba4/private/sam.ldb -b "$userbase" objectClass=group cn $fields`;
    my $cn;
    my $oldkey;
    foreach my $line (split /\n/, $groups_text) {
        $cn = $1 if ($line =~ /dn: CN=(.+),CN=Users/);
        my $key;
        my $val;
        if ($cn) {
            if ($line =~ /(\w+): (.*)/) {
                $key = $1;
                $val = $2;
            } elsif ($line =~ /(\w+):: (.*)/) {
                $key = $1;
                $val = decode_base64($2);
            } elsif ($line =~ /^ (.+)/) {
                $val = $1;
            }
        }
        if ($key) {
            $val = $1 if ($key ne 'dn' && $val =~ /^CN=(.+),CN=Users,/);
            if ($groups{$cn}->{$key}) { # Property already has value, add new line
                $groups{$cn}->{$key} .= "\n" . $val;
            } else {
                $groups{$cn}->{$key} = $val;
            }
            $oldkey = $key;
        } elsif ($val && $oldkey) {
            $groups{$cn}->{$oldkey} .= $val;
        }
    }
    foreach my $group (values %groups) {
        foreach my $prop (@groupprops) {
            $group->{$prop} = '' unless ($group->{$prop}); # Get rid of nulls
        }
    # Generate write lists
        my $groupwritelist = '';
        my $gfile = "/etc/samba/smb.conf.group.$group->{cn}";
        if (-e $gfile) {
            my $cmd = qq[cat "$gfile" | grep "write list"];
            my $wlist = `$cmd`;
            chomp $wlist;
            if ($wlist =~ /write list =(.+)/) {
                $wlist = $1;
                my @writers = quotewords('\s+', 1, $wlist);
                my @vals;
                foreach my $writer (@writers) {
                    $writer = $2 if ($writer =~ /(\+)?".+\\(.+)"/);
                    push(@vals, "$writer") if ($writer);
                }
                $groupwritelist = join(", ", @vals);
            }
        }
        $group->{writelist} = $groupwritelist;

    }
    return %groups;
}

my $sgroups = <<END
Allowed RODC Password Replication Group
Enterprise Read-Only Domain Controllers
Denied RODC Password Replication Group
Pre-Windows 2000 Compatible Access
Windows Authorization Access Group
Certificate Service DCOM Access
Network Configuration Operators
Terminal Server License Servers
Incoming Forest Trust Builders
Read-Only Domain Controllers
Group Policy Creator Owners
Performance Monitor Users
Cryptographic Operators
Distributed COM Users
Performance Log Users
Remote Desktop Users
Account Operators
Event Log Readers
RAS and IAS Servers
Backup Operators
Domain Controllers
Server Operators
Enterprise Admins
Print Operators
Administrators
Domain Computers
Cert Publishers
DnsUpdateProxy
Domain Admins
Domain Guests
Schema Admins
Domain Users
Replicator
IIS_IUSRS
DnsAdmins
Guests
Users
END
;
my @system_groups = split(/\n/, $sgroups);
%sysgroups = map { lc $_ => $_ } @system_groups;

1;
