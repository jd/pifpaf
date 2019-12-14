connector {
    name: broker
    role: route-container
    host: 127.0.0.1
    port: {{ ARTEMIS_PORT }}
    sasl-mechanisms: ANONYMOUS
    linkCapacity: 1000
    stripAnnotations:no
}

address {
    prefix: unicast
    distribution: closest
}

address {
    prefix: exclusive
    distribution: closest
}

address {
    prefix: broadcast
    distribution: multicast
}

address {
    prefix: openstack.org/om/rpc/multicast
    distribution: multicast
}

address {
    prefix: openstack.org/om/rpc/unicast
    distribution: closest
}

address {
    prefix: openstack.org/om/rpc/anycast
    distribution: balanced
}

linkRoute {
    prefix: openstack.org/om/notify
    connection: broker
    dir: in
}

linkRoute {
    prefix: openstack.org/om/notify
    connection: broker
    dir: out
}
