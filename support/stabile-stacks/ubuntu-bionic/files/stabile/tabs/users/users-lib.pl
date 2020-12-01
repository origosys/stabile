#!/usr/bin/perl

use MIME::Base64 qw( decode_base64 );

@userprops = ("givenName", "sn", "mail", "telephoneNumber");
@userpropnames = ("First name", "Last name", "Email", "Phone");

sub users {
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
        my $drows;
        my $dheaders;
        my $i = 0;
        foreach my $prop (@userprops) {
            my $propname = $userpropnames[$i];
            $drows .= <<END
                <tr>
                    <td>$propname:</td><td class="passwordform"><input type="text" name="edituser_$prop" id="edituser_$prop" /></td>
                </tr>
END
;
            $dheaders .= "            <th>$propname</th>\n";
            $i++;
        }
        my $form = <<END
<div class="tab-pane" id="users">
    <div style="width:100%; height:310px; overflow-y:scroll;">
      <table class="table table-condensed table-striped small" id="users_table" style="width: 100%; border:none;">
        <thead>
          <tr>
            <th>Username</th>
$dheaders
            <th>DN</th>
          </tr>
        </thead>
        <tbody>

        </tbody>
      </table>
    </div>
    <div style="margin-top:6px; padding-top:4px ; border-top:2px solid #DDDDDD">
        <button class="btn btn-default" id="update_users" title="Click to check refresh user list." rel="tooltip" data-placement="top" onclick="\$('[rel=tooltip]').tooltip('hide'); updateSambaUsers(); return false;"><span class="glyphicon glyphicon-repeat" id="urglyph"></span></button>
        <button class="btn btn-default" id="new_user" title="Click to add a domain user." rel="tooltip" data-placement="top" onclick="\$('[rel=tooltip]').tooltip('hide'); editSambaUser(); return false;">New user</button>
    </div>
</div>

<div class="modal" id="editUserDialog" tabindex="-1" role="dialog" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-body">
        <h4 class="modal-title" id="user_label">Edit user</h4>
        <form id="edit_user_form" class="small" method="post" action="index.cgi?action=savesambauser\&tab=users" autocomplete="off">
            <table width="100\%" style="padding:2px;">
                <tr>
                    <td width="200">Username:</td><td class="passwordform"><input readonly type="text" name="edituser_cn" id="edituser_cn" value="" /></td>
                </tr>
$drows
                <tr>
                    <td>Password:</td><td class="passwordform"><input type="text" name="edituser_pwd" id="edituser_pwd" value="" /></td>
                </tr>
            </table>
            <!-- input type="hidden" name="edituser_cn" id="edituser_cn" / -->
            <input type="hidden" name="edituser_dn" id="edituser_dn" />
            <input type="hidden" name="edituser_sAMAccountName" id="edituser_sAMAccountName" />
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-default pull-left" data-dismiss="modal" onclick="confirmUserAction('delete', \$('#edituser_cn').val());">Delete</button>
        <button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-primary" onclick="saveSambaUser(\$('#edituser_cn').val());">Save</button>
      </div>
    </div>
  </div>
</div>
END
;
        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs

        my $editjs;
        my $newjs;
        my $tablejs;
        my $nprops = scalar @userprops;
        my $i=1;
        foreach my $prop (@userprops) {
            $editjs .= qq|\$('#edituser_$prop').val(editrow["$prop"]+"");\n|;
            $newjs .= qq|\$("#edituser_$prop").val("");\n|;
            $tablejs .= qq|{ data: "$prop" },\n|;
            $i++;
        }

        my $js = <<END
    \$(document).ready(function () {
        sambaUsersTable = \$('#users_table').DataTable({
//            scrollY: 280,
            searching: false,
            paging: false,
            columns: [
                { data: "cn" },
                $tablejs
                { data: "dn" }
            ],
            columnDefs: [
                {
                    targets: [ 0 ],
                    render: function ( data, type, row ) {
                                    return ('<a href="#" onclick="editSambaUser(\\''+ data + '\\');">' + data +'</a>');
                                }
                },
                {
                    targets: [ 5 ],
                    visible: false,
                    searchable: false
                }
            ],
            ajax: {
                url: "index.cgi?tab=users\&action=listsambausers",
                dataSrc: ""
            }
        });
    });

    function updateSambaUsers() {
        \$('#update_users').prop( "disabled", true);
//        \$('#urglyph').attr('class','glyphicon glyphicon-refresh');
        sambaUsersTable.ajax.reload(function ( json ) {
                                        \$('#update_users').prop( "disabled", false);
//                                        \$('#urglyph').attr('class','glyphicon glyphicon-repeat');
                                    });
    }

    function editSambaUser(cn) {
        \$('#editUserDialog').modal({'backdrop': false, 'show': true});
        var editrow = [];
        if (cn) {
            \$('#edituser_cn').val(cn);
            \$('#edituser_cn').prop("readonly",true);
            \$.each(sambaUsersTable.data(), function(index, irow) {
                if (irow["cn"] == cn) editrow = irow;
            });
            if(editrow) {
                \$('#edituser_dn').val(editrow["dn"]);
                \$('#edituser_sAMAccountName').val(editrow["sAMAccountName"]);
                $editjs
            }
            \$('#user_label').html("Edit user");
        } else {
        // New user
            \$('#edituser_cn').val('');
            \$('#edituser_cn').prop("readonly",false);
            \$('#edituser_dn').val("new");
            $newjs;
            \$('#user_label').html("New user");
        }
        \$('#edituser_pwd')[0].type = "password";
        // A little fight against auto-fill-out
        setTimeout(function(){
            \$('#edituser_pwd').val('');
            if (!editrow["telephoneNumber"]) \$('#edituser_telephoneNumber').val('');
        }, 100);
        \$('#edituser_cn').focus();
    }

    function saveSambaUser(user) {
        var editrow = [];
        console.log("Saving user", user);

        \$.each(sambaUsersTable.data(), function(index, irow) {
            if (irow["cn"] == user) editrow = irow;
        });

        \$.each(editrow, function( prop, oldval ) {
            var newval = \$("#edituser_" + prop).val();
            if (!newval && oldval) \$("#edituser_" + prop).val("--");
        });

        \$.post( "index.cgi?action=savesambauser\&tab=users", \$("#edit_user_form").serialize())
        .done(function( data ) {
            salert(data);
            updateSambaUsers();
        })
        .fail(function() {
            salert( "An error occurred :(" );
        });

        \$('#edituser_pwd')[0].type = "text";
        \$('#editUserDialog').modal('hide');
        return(false);
    }

    function deleteSambaUser() {
        var editrow = [];
        console.log("Deleting user", \$("#edituser_cn").val());

        \$.post( "index.cgi?action=deletesambauser\&tab=users", \$("#edit_user_form").serialize())
        .done(function( data ) {
            salert(data);
            updateSambaUsers();
        })
        .fail(function() {
            salert( "An error occurred :(" );
        });

        \$('#edituser_pwd')[0].type = "text";
        \$('#editUserDialog').modal('hide');
        return(false);
    }

    function confirmUserAction(action, cn) {
        if (action == 'delete') {
            \$('#confirmdialog').prop('actionform', "deleteSambaUser");
            \$('#confirmdialog').modal({'backdrop': false, 'show': true});
            return false;
        }
    };


END
;
        return $js;

    } elsif ($action eq 'deletesambauser' && defined $in{edituser_cn}) {
        my $res = "Content-type: text/html\n\n";
        my $user = $in{edituser_cn};
        if (lc $user eq 'guest' || lc $user eq 'administrator' || lc $user eq 'krbtgt') {
            $res .= "Please do not delete system users";
        } else {
            my $cmd = qq[samba-tool user delete "$user"];
            $cmdres .= `$cmd`;
            if ($cmdres =~ /Deleted/) {
                $res .= "User deleted: $cmdres";
                my $dir = "/mnt/data/groups/$user";
                if (scalar <"$dir/*">) {
                    unless (-d "/mnt/data/archive") {
                        `mkdir -p /mnt/data/archive`;
                        `ln -s /mnt/data/archive /mnt/data/users/administrator/`;
                    }
                    my $datestr = localtime() . '';
                    `mv "/mnt/data/groups/$user" "/mnt/data/user/archive/$user ($datestr)"`;
                    $res .= " User share not empty - archived. ";
                }
            } else {
                $res .= "User not deleted - there was a problem ($cmd, $cmdres)";
            }
        }
        return $res;

    } elsif ($action eq 'savesambauser' && defined $in{edituser_dn}) {
        my $res = "Content-type: text/html\n\n";
        my $cmd;
        my $cmdres;
        my $cmdalert;
        my $isnew;
        if ($in{edituser_dn} eq 'new') {
            $isnew = 1;
            if ($userbase && $in{edituser_cn} && $in{edituser_pwd}) {
                $in{edituser_dn} = "CN=$in{edituser_cn},$userbase";
                $cmd = qq[samba-tool user add "$in{edituser_cn}" "$in{edituser_pwd}"];
#                $cmd .= qq[ --mail-address "$in{edituser_mail}"] if ($in{edituser_mail});
#                $cmd .= qq[ --telephone-number "$in{edituser_telephoneNumber}"] if ($in{edituser_telephoneNumber});
#                $cmd .= qq[ --given-name "$in{edituser_givenName}"] if ($in{edituser_givenName});
#                $cmd .= qq[ --surname "$in{edituser_sn}"] if ($in{edituser_sn});
                $cmdres .= `$cmd 2>\&1`;
                `mkdir "/mnt/data/users/$in{edituser_cn}"`;
                `chmod 777 "/mnt/data/users/$in{edituser_cn}"`;
            } else {
                $cmdalert .= "no userbase" if (!$userbase);
                $cmdalert .= "Please provide a user name" if (!$in{edituser_cn});
                $cmdalert .= "Please provide a password" if (!$cmdalert && !$in{edituser_pwd});
            }
        }
#        } else {
            my $laction;
            $laction .= "changetype: modify\n";
            my $changes;
            foreach my $prop (@userprops) {
                if ($in{"edituser_$prop"} eq '--') {
                    $laction .= "delete: $prop\n";
                    $laction .= "-\n";
                } elsif ($in{"edituser_$prop"}) {
                    $changes = 1;
                    $laction .= "replace: $prop\n";
                    $laction .= "$prop: ". $in{"edituser_$prop"} . "\n";
                    $laction .= "-\n";
                }
            };

            my $ldif = <<END
dn: $in{edituser_dn}
$laction
END
;
            $cmd = qq[echo "$ldif"| ldbmodify -H /opt/samba4/private/sam.ldb --] if ($changes);
            $cmdres .= `$cmd 2>\&1` if ($cmd);

            if ($in{edituser_pwd} && !$isnew) {
                $cmd = qq[samba-tool user setpassword $in{edituser_cn} --newpassword=$in{edituser_pwd}];
                $cmdres .=  `$cmd 2>\&1`;
                if ($cmdres =~ /password OK/) {
                    $res .=  "The Samba password was changed! ";
                } else {
                    $res .= "The Samba password was NOT changed! ";
                }
            }
#        }

        if ($cmdalert) {
            $res .= $cmdalert;
        } elsif (!$cmd) {
            $res .= "Nothing to save";
        } elsif ($cmdres =~ /success/) {
            $res .= "User saved: $cmdres";
        } else {
            $res .= "User not saved ($cmd, $cmdres)";
            $cmd =~ s/"/\\"/;
            `echo "$cmdres" >> /tmp/ldbmodify.out`;
        }
        return $res;

    } elsif ($action eq 'listsambausers') {
        my %sambausers = getUsers();
        my $res = "Content-type: application/json\n\n";
        my @uarray = values %sambausers;
        my $ujson = to_json(\@uarray, {pretty=>1});
        $res  .= $ujson;
        return $res;

    } elsif ($action eq 'upgrade') {

# This is called from origo-ubuntu.pl when rebooting and with status "upgrading"
    } elsif ($action eq 'restore') {

    }

}

sub getUsers {
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

    my %users;
    my $fields = join(" ", @userprops) . ' sAMAccountName';
    my $users_text = `ldbsearch -H /opt/samba4/private/sam.ldb -b "$userbase" objectClass=user cn $fields`;
    my $cn;
    foreach my $line (split /\n/, $users_text) {
        $cn = $1 if ($line =~ /dn: CN=(.+),CN=Users/);
        $users{$cn}->{$1} = $2 if ($cn && $line =~ /(\w+): (.*)/);
        $users{$cn}->{$1} = decode_base64($2) if ($cn && $line =~ /(\w+):: (.*)/);
    }
    foreach my $user (values %users) {
        foreach my $prop (@userprops) {
            $user->{$prop} = '' unless ($user->{$prop});
        }
    }
    return %users;
}

1;
