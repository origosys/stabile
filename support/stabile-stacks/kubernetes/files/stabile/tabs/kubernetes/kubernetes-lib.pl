#!/usr/bin/perl

use JSON;
use YAML::XS qw "LoadFile Load Dump";

sub kubernetes {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form' || $action eq 'kubeform') {
        my $form;
        my $token = `cat /root/admin-user.token`;
        chomp $token;
        my $allow = `cat /etc/apache2/sites-available/kubernetes-ssl.conf`;
        my $kubelimit = $1 if ($allow =~ /allow from (.+)/);
        my $curip = qq|<div style="font-size: 13px;">leave empty to disallow all access, your current IP is <a style="text-decoration: none;" href="#" onclick="\$('#limitkube').val('$ENV{HTTP_X_FORWARDED_FOR} ' + \$('#limitkube').val());">$ENV{HTTP_X_FORWARDED_FOR}</a></div>| if ($ENV{HTTP_X_FORWARDED_FOR});

        my $kubepwform = <<END
    <form class="passwordform" id="kubepassword_form" action="index.cgi?action=kubepassword&tab=kubernetes" method="post" onsubmit="limitKubeSpinner('kubepassword'); \$('#kubepassword').val(''); return false;" accept-charset="utf-8" id="linform" autocomplete="off">
        <div class="small">Set password for dashboard user "admin":</div>
        <div class="row">
            <div class="col-sm-10">
                <input id="kubepassword" type="password" name="kubepassword" autocomplete="off" value="" class="password">
            </div>
            <div class="col-sm-2">
                <button class="btn btn-default" type="submit" id="kubepassword_button">Set!</button>
            </div>
        </div>
    </form>
    <div class="small">
        After allowing access from your IP address, you can access the <a target="_blank" href="https://$externalip:10002/">dashboard</a> with username 'admin'.<br>
        You can also download a <a href="kubeconfig" download="kubeconfig">kubeconfig file</a> to access your cluster with kubectl.
    </div>
END
        ;

        my $kubelimitform = <<END
        <h6>Dashboard and kubeconfig</h6>
    <div>
		<form class="passwordform" id="limitkube_form" action="index.cgi?action=limitkube&tab=kubernetes" method="post" onsubmit="limitKubeSpinner(); return false;" accept-charset="utf-8">
			<div class="small">Allow Kubernetes kubectl and dashboard login from:</div>
			<div class="row">
				<div class="col-sm-10">
					<input id="limitkube" type="text" name="limitkube" value="$kubelimit" placeholder="IP address or network, e.g. '192.168.0.0/24 127.0.0.1'">
					$curip
				</div>
				<div class="col-sm-2">
					<button class="btn btn-default" type="submit" id="limitkube_button">Set!</button>
				</div>
			</div>
		</form>
$kubepwform
    </div>
END
        ;
        my $tokenform = <<END # Not used - we proxy through Apache
        <div class="small">Dashboard access token:</div>
        <pre style="margin-bottom:0px;"><code id="tokenbar">$token</code></pre>
        <button class="btn-copy btn" data-clipboard-action="copy" data-clipboard-target="#tokenbar">Copy to clipboard</button>
END
        ;
        my $ipform = <<END
        <a name="kubeaddresses"></a>
        <h6>IPv4 addresses</h6>
        <div>
        <div class="small">Below are the IPv4 addresses available for your loadbalancers.<br>Please be careful not to remove any addresses that are in use by your loadbalancers.<br>Addresseses are allocated by <a href="https://metallb.universe.tf/" target="_blank">MetalLB</a> from top to bottom. Drag entries to reorder.</div>
        <div class="small">
            <ul id="ipv4sortable" style="width: 300px;">
            </ul>
        </div>
        <form class="passwordform small" id="kubeip_form" action="index.cgi?action=kubeip&tab=kubernetes" method="post" onsubmit="limitKubeSpinner('kubeip'); return false;" accept-charset="utf-8">
            <input id="kubeip_button" type="button" value="+ add external IP address" class="btn btn-sm btn-success kube" onclick="\$('#kubeip').val('external'); \$('#kubeip_form').submit();">
            <input id="kubeip_button2" type="button" value="+ add internal IP address" class="btn btn-sm btn-info kubebutton" onclick="\$('#kubeip').val('internal'); \$('#kubeip_form').submit();">
            <input id="kubeip_button3" type="button" value="+ add IP address mapping" class="btn btn-sm btn-warning kubebutton" onclick="\$('#kubeip').val('mapping'); \$('#kubeip_form').submit();">
            <input type="hidden" name="kubeip" id="kubeip">
            <input type="hidden" name="kubeips" id="kubeips">
        </form>
        </div>
        <script>setTimeout(function() {loadKubeAddresses();}, 1000);</script>
END
        ;

        my $storageform = <<END
<a name="kubeclasses"></a>
<h6>Storage</h6>
<div>
<div class="small">Below are the Storage Classes available for Persistent Volume Claims.<br>We use <a href="http://openebs.io" target="_blank">OpenEBS</a> for local storage, and <a href="https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner" target="_blank">this</a> for NFS storage. </div>
<div class="small">
    <ul id="storageclasses" style="width: 300px;">
    </ul>
</div>
<form class="passwordform small" id="kubeclasses_form" action="index.cgi?action=kubeclasses&tab=kubernetes" method="post" onsubmit="limitKubeSpinner('kubeclasses'); return false;" accept-charset="utf-8">
    <input type="hidden" name="kubeclass" id="kubeclass">
    <input type="hidden" name="oldkubeclass" id="oldkubeclass">
</form>
</div>
<script>setTimeout(function() {loadKubeClasses();}, 1000);</script>
END
        ;

        if (-e "/usr/share/webmin/stabile/tabs/kubernetes/joincmd.sh") {
            $form = <<END
    <div id="accordion">
        $kubelimitform
        $ipform
        $storageform
    </div>
END
            ;
        } else {
            my $status = `tail -n15 /root/initout.log`;
            $form = <<END
    <script>
        setTimeout(function() {
            \$.get("index.cgi?action=kubeform&tab=kubernetes", function(result) {
                \$("#kubernetes").html(result);
            });
        }, 3000);
    </script>
    <div class="tab-pane container" id="kubernetes">
        <table><tr><td>
            <div class="sk-wave">
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
            </div>
        </td><td>
            <h5 style="margin-left: 20px;">Preparing Kubernetes...</h5>
        </td><tr></table>
        <pre>$status
        </pre>
    </div>
END
        }
        if ($action eq 'form') {
            return <<END
    <style>
        :root {
          --no-sk-size: 200px;
        }
        .ui-accordion-header {
            border: none;
            margin-left:0;
            background: none;
            padding-left:0;
            cursor: pointer;
        }
        .ui-accordion-header-icon {
            padding: 0 6px 0 0;
            font-size: 70%;
            cursor: pointer;
        }
    </style>
    <div class="tab-pane container" id="kubernetes">
        $form
    </div>
END
            ;
        } else {
            return <<END
Content-type: text/htm

$form
<script>
    \$( "#accordion" ).accordion({header: "h6", heightStyle: "content", icons: { "header": "glyphicon glyphicon-chevron-right", "activeHeader": "glyphicon glyphicon-chevron-down" }});
</script>
END
        }

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
    \$("#currentwp").attr("href", "https://$externalip:10002/");
    \$("#currentwp").text("to Kubernetes Dashboard");

    function submitIPs() {
        var ips = JSON.stringify(\$("#ipv4sortable").sortable("toArray"));
        if (ips !== \$("#kubeips").val()) {
            \$("#kubeips").val(ips);
            \$("#kubeip").val('');
            limitKubeSpinner('kubeip');
        }
    }

    function limitKubeSpinner(target) {
        if (!target) target = "limitkube";
        \$("#" + target + "_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        \$(".kubebutton").prop("disabled", true );
        \$.post('index.cgi?action=' + target + '&tab=kubernetes', \$('form#' + target + '_form').serialize(), function(data) {}
        ,'json'
        ).done(function( data ) {
            salert(data.message);
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
            \$(".kubebutton").prop("disabled", false );
            if (target == 'kubeip') loadKubeAddresses();
            else if (target == 'kubeclasses') loadKubeClasses();
        }).fail(function() {
            salert( "An error occurred :(" );
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
            \$(".kubebutton").prop("disabled", false );
            loadKubeAddresses();
        });
    }

    function loadKubeAddresses() {
        var addresses = "<i>No addresses assigned yet</i>";
        \$.get("index.cgi?action=getkubeaddresses&tab=kubernetes", function(result) {
            if (result.addresses && result.addresses.length>0) addresses = '';
            \$.each(result.addresses, function(index, val) {
                var comment = result.comments[index];
                var regexp = /(\\d+\.\\d+\.\\d+\.\\d+)/;
                var comment1 = comment.replace(regexp, '<a href=http://\$1 target=_blank>\$1</a>');
                var trash = '<a href="#kubeaddresses" onclick="\$(\\'#kubeip\\').val(\\'' + val + '\\'); \$(\\'#kubeip_form\\').submit();" style="text-decoration:none;"><span class="glyphicon glyphicon-trash kubebutton" style="float:right; margin:7px;" title="delete"></span></a>';
                trash1 = (result.services[index])?'<span class="glyphicon glyphicon-transfer kubebutton" title="in use by: ' +  result.services[index] + '" style="float:right; margin:7px;"></span>' : trash;

                addresses += '<li class="ui-state-default" id="' + val + '-' + comment + '" style="cursor:grab; list-style-type: none;"><span class="glyphicon glyphicon-resize-vertical"></span> <a href="http://' + val + '" target="_blank">' + val + '</a> <span class="small">' + comment1 +  '</span> ' + trash1 + ' </li> ';
            });
            \$("#ipv4sortable").html(addresses);
        });
    }

    function loadKubeClasses() {
        var classes = "<i>No Storage Classes defined</i>";
        \$.get("index.cgi?action=getkubeclasses&tab=kubernetes", function(result) {
            if (result.items && result.items.length>0) {
                classes = '';
	            \$.each(result.items, function(index, item) {
                    var name = item.metadata.name;
	                var isdefault = item.metadata.annotations["storageclass.kubernetes.io/is-default-class"];
                    var makedefault = '<a href="#kubeclasses" onclick="\$(\\'#kubeclass\\').val(\\'' + name + '\\'); \$(\\'#kubeclasses_form\\').submit();" style="text-decoration:none;"><span class="glyphicon glyphicon-star-empty kubebutton" style="float:right; margin:7px;" title="make default"></span></a>';
	                var defaultbutton = (isdefault==='true') ? ' <span class="small">(default)</span>' : makedefault;
                    classes += '<li class="ui-state-default" id="' + name + '" style="list-style-type: none;"><span class="glyphicon glyphicon-hdd kubebutton" style="margin:7px;"></span>' + name + defaultbutton + ' </li> ';
                    if (isdefault==='true') {
                        \$("#oldkubeclass").val(name);
                    }
	            });
	            \$("#storageclasses").html(classes);
            }
        });
    }

    new ClipboardJS('.btn-copy');
    \$("#ipv4sortable").sortable({
        stop: function( event, ui ) {submitIPs();},
        cursor: "grabbing"
    });
    \$( "#ipv4sortable" ).disableSelection();
    \$( "#accordion" ).accordion({header: "h6", heightStyle: "content", icons: { "header": "glyphicon glyphicon-chevron-right", "activeHeader": "glyphicon glyphicon-chevron-down" }});

    var linkElement = document.createElement("link");
    linkElement.rel = "stylesheet";
    linkElement.href = "tabs/kubernetes/spinkit.css";
    document.head.appendChild(linkElement);
END
;
        return $js;

    } elsif ($action eq 'kubeip') {
        my $message = "External or internal...?";
        my @configlines;
        my $config_str = '';
        if ($in{kubeip}) {
            my $kubeip = $in{kubeip};
            my $yaml_obj = LoadFile('tabs/kubernetes/manifests/metallb-addresses.yaml');
            my $configyaml = $yaml_obj->{'data'}->{'config'};
            @configlines = split("\n", $configyaml);
            my $netname = $appinfo{name};
            $netname = $1 if ($netname =~ /(.+)\.\d+/);
            if ($kubeip eq 'external' || $kubeip eq 'internal' || $kubeip eq 'mapping') { # Add an ip address
                my $iptype = $kubeip . 'ip';
                $iptype = "ipmapping" if ($kubeip eq 'mapping');
                my $res = `curl -ks -X POST -d '{"type":"$iptype", "name": "$netname.$kubeip", "systems": "$appinfo{system}"}' https://$gw/stabile/networks`;
                my $ip;
                my $comment = $iptype;
                if ($kubeip eq 'mapping') {
                    my $externalip;
                    $externalip = $1 if ($res =~ /Status=OK .+ external IP: (\d+\.\d+\.\d+\.\d+)/);
                    $ip = $1 if ($res =~ /Status=OK .+ internal IP: (\d+\.\d+\.\d+\.\d+)/);
                    if ($ip && $externalip) {
                        $comment = "$iptype $externalip"
                    } else {
                        $comment = "internalip";
                    }
                } else {
                    $ip = $1 if ($res =~ /Status=OK .+ IP: (\d+\.\d+\.\d+\.\d+)/);
                }
                if ($ip) {
                    $message = "Allocated IP address $ip $appinfo{system}";
                    push @configlines, "  - $ip-$ip #" . $comment;
                    $res = `curl -ks -X POST -d '{"uuid": "$ip", "action": "activate"}' https://$gw/stabile/networks`;
                }
                else {
                    $message = "Unable to allocate $iptype - check your quota";
                }
            } elsif ($kubeip =~ /\d+\.\d+\.\d+\.\d+/) { # Remove an ip address
                my @newlines = ();
                my $res;
                my $cmd;
                foreach my $line (@configlines) {
                    if ($line =~ /$kubeip/) {
                        $cmd = qq|curl -ks -X GET "https://$gw/stabile/networks?action=deactivate\&uuid=$kubeip"|;
                        $res = `$cmd`;
                        $cmd = qq|curl -ks -X DELETE "https://$gw/stabile/networks?action=remove\&force=1\&uuid=$kubeip"|;
                        $res = `$cmd`;
                        chomp $res;
                    } else {
                        push(@newlines, $line);
                    }
                }
                $message = "Removing: $kubeip";
                @configlines = @newlines;
            } else {
                $message = "Invalid net type: $kubeip";
            }
            $config_str = '    ' . join("\n    ", @configlines) if (@configlines);
        } elsif ($in{kubeips}) { # Rearrange ip addresses
            my $addrs_json = from_json($in{kubeips});
            my @addresses = @{$addrs_json};
            foreach my $line (@addresses) {
                if ($line =~ /(\d+\.\d+\.\d+\.\d+)-(.+)/) {
                    my $address = $1;
                    my $comment = "$2";
                    push @configlines, "$address-$address #$comment";
                }
            }
            $config_str = '\n      - ' . join("\n      - ", @configlines) if (@configlines);
            $config_str = <<END
    address-pools:
    - name: default
      protocol: layer2
      addresses:$config_str
END
;
            $message = "Got it!";
        }
        my $yaml_out = <<END
apiVersion: v1
kind: ConfigMap
metadata:
  namespace: default
  name: config
data:
  config: |
$config_str
END
        ;
        `echo "$yaml_out" > tabs/kubernetes/manifests/metallb-addresses.yaml`;
        my $res = `kubectl apply -f tabs/kubernetes/manifests/metallb-addresses.yaml`;
        chomp $res;
        $message .= " - applying $res";
        return qq|Content-type: application/json\n\n{"message": "$message"}|;

    } elsif ($action eq 'kubeclasses') {
        my $message = "Please supply a storage class!";
        if (defined $in{kubeclass}) {
            my $sclass = $in{kubeclass};
            my $res = `KUBECONFIG=/etc/kubernetes/admin.conf kubectl patch storageclass $sclass -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}' 2>\&1`;
            chomp $res;
            if ($in{oldkubeclass}) {
                my $res2 = `KUBECONFIG=/etc/kubernetes/admin.conf kubectl patch storageclass $in{oldkubeclass} -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}' 2>\&1`;
                chomp $res2;
            }
            $message = "OK, set $sclass as default storage class. $res $res2";
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;

    } elsif ($action eq 'getkubeclasses') {
        my $json = `kubectl get storageclasses -o json`;
        return qq|Content-type: application/json\n\n| . $json;

    } elsif ($action eq 'getkubeaddresses') {
        my $yaml_obj = LoadFile('tabs/kubernetes/manifests/metallb-addresses.yaml');
        my $configyaml = $yaml_obj->{'data'}->{'config'};
        my @configlines = split("\n", $configyaml);
        my @addrs;
        my @comments;
        my @services;
        my %ingresses;
        my $svc_obj = from_json(`kubectl get services -o json`);
        foreach my $svc (@{$svc_obj->{items}}) {
            if ($svc->{status}
                && $svc->{status}->{loadBalancer}
                && $svc->{status}->{loadBalancer}->{ingress}
                && $svc->{status}->{loadBalancer}->{ingress}->[0]
                && $svc->{status}->{loadBalancer}->{ingress}->[0]->{ip}
            ) {
                my $ip = $svc->{status}->{loadBalancer}->{ingress}->[0]->{ip};
                if ($ip =~ /\d+\.\d+\.\d+\.\d+/) {
                    $ingresses{$ip} = $svc->{metadata}->{name};
                }
            }
        }
        foreach my $addr(@configlines) {
            if ($addr =~ /(\d+\.\d+\.\d+\.\d+)-(\d+\.\d+\.\d+\.\d+) ?#?(.*)/) {
                push @addrs, $1;
                push @comments, $3;
                push @services, ($ingresses{$1})?$ingresses{$1} : '';
            }
        }
        my $res = {addresses => \@addrs, comments => \@comments, services => \@services};
        return qq|Content-type: application/json\n\n| . to_json($res);

    } elsif ($action eq 'limitkube') {
        my $message = "Please supply a limit!";
        if (defined $in{limitkube}) {
            my $limit = $in{limitkube};
            my ($validlimit, $sshlimit, $mess) = validate_limit($limit);
            my $conf = "/etc/apache2/sites-available/kubernetes-ssl.conf";
            if ($validlimit) {
                if (`grep 'allow from' /etc/apache2/sites-available/kubernetes-ssl.conf`)
                {
                    $message =  "Kubernetes apiserver and dashboard access was changed!";
                    my @limits = split(" ", $validlimit);
                    $message .= `iptables -D INPUT -p tcp --dport 6443 -j DROP 2>/dev/null`;
                    foreach my $lim (@limits) {
                        $message .= `iptables -D INPUT -p tcp --dport 6443 -s $lim -j ACCEPT 2>/dev/null`;
                        $message .= `iptables -A INPUT -p tcp --dport 6443 -s $lim -j ACCEPT 2>/dev/null`;
                    }
                    $message .= `iptables -A INPUT -p tcp --dport 6443 -j DROP 2>/dev/null`;
                    $message .= `perl -pi -e 's/allow from (.*)/allow from $validlimit/;' $conf`;
                } else {
                    $message =  "Unable to process kubernetes-ssl.conf!";
                }
                `systemctl reload apache2`;
            } else {
                $message =  $mess;
            }
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;

    } elsif ($action eq 'kubepassword') {
        my $message = "Please supply a password!";
        if (defined $in{kubepassword} && $in{kubepassword} =~ /^\S+$/) {
            my $pwd = $in{kubepassword};
            my $conf = "/etc/apache2/kubepasswords";
            if ($pwd) {
                unless (system(qq|htpasswd -b $conf admin $pwd|))
                {
                    $message =  "Kubernetes dashboard password was changed!";
                } else {
                    $message =  "Unable to change password!";
                }
            } else {
                $message =  $mess;
            }
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;
# This is called from index.cgi (the UI)
    } elsif ($action eq 'upgrade') {
        my $res;
        return $res;

# This is called from stabile-ubuntu.pl when rebooting and with status "upgrading"
    } elsif ($action eq 'restore') {
        my $res;
        return $res;

    } elsif ($action eq 'getkubetoken') {
        my $message;
        $message .= "<div class=\"message\">Retrived token</div>";
        return $message;
    }
}


1;
