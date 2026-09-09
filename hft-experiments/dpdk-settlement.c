#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_ip.h>
#include <rte_udp.h>
#include <rte_ether.h>

#define RX_RING_SIZE 1024
#define TX_RING_SIZE 1024
#define NUM_MBUFS 8192
#define MBUF_CACHE_SIZE 250
#define BURST_SIZE 32

#define CODE_LEN 32

/* ---- Resting order (single level, demo) ---- */
struct resting_order {
    char asset[4];
    char price[6];
    char amount[6];
    int  active;
};

static struct resting_order book = {
    .asset  = { 'A','A','A','B' },
    .price  = { 'A','A','A','n','0','A' },
    .amount = { 'A','A','A','n','0','A' },
    .active = 1
};

/* Fixed-length lexicographic compare */
static inline int cmp(const char *a, const char *b, int len) {
    for (int i = 0; i < len; i++) {
        if (a[i] != b[i])
            return a[i] - b[i];
    }
    return 0;
}

int main(int argc, char **argv)
{
    int ret = rte_eal_init(argc, argv);
    if (ret < 0)
        rte_exit(EXIT_FAILURE, "EAL init failed\n");

    uint16_t port_id = 0;

    struct rte_mempool *mbuf_pool =
        rte_pktmbuf_pool_create(
            "MBUF_POOL",
            NUM_MBUFS,
            MBUF_CACHE_SIZE,
            0,
            RTE_MBUF_DEFAULT_BUF_SIZE,
            rte_socket_id()
        );

    if (!mbuf_pool)
        rte_exit(EXIT_FAILURE, "Cannot create mbuf pool\n");

    struct rte_eth_conf port_conf = {0};

    rte_eth_dev_configure(port_id, 1, 1, &port_conf);
    rte_eth_rx_queue_setup(port_id, 0, RX_RING_SIZE,
                            rte_eth_dev_socket_id(port_id),
                            NULL, mbuf_pool);
    rte_eth_tx_queue_setup(port_id, 0, TX_RING_SIZE,
                            rte_eth_dev_socket_id(port_id),
                            NULL);

    rte_eth_dev_start(port_id);

    printf("DPDK settlement fast-path running\n");

    struct rte_mbuf *bufs[BURST_SIZE];

    while (1) {
        uint16_t nb_rx =
            rte_eth_rx_burst(port_id, 0, bufs, BURST_SIZE);

        if (nb_rx == 0)
            continue;

        for (uint16_t i = 0; i < nb_rx; i++) {
            struct rte_mbuf *m = bufs[i];

            struct rte_ether_hdr *eth =
                rte_pktmbuf_mtod(m, struct rte_ether_hdr *);

            if (eth->ether_type != rte_cpu_to_be_16(RTE_ETHER_TYPE_IPV4))
                goto forward;

            struct rte_ipv4_hdr *ip =
                (struct rte_ipv4_hdr *)(eth + 1);

            if (ip->next_proto_id != IPPROTO_UDP)
                goto forward;

            struct rte_udp_hdr *udp =
                (struct rte_udp_hdr *)((uint8_t *)ip +
                (ip->ihl * 4));

            char *code = (char *)(udp + 1);

            if (rte_pktmbuf_data_len(m) <
                sizeof(*eth) + sizeof(*ip) +
                sizeof(*udp) + CODE_LEN)
                goto forward;

            /* delimiter check */
            if (code[7] != '~' || code[12] != '~' ||
                code[19] != '~' || code[26] != '~')
                goto drop;

            if (!book.active)
                goto forward;

            /* asset check */
            if (memcmp(&code[8], book.asset, 4) != 0)
                goto forward;

            /* price check */
            if (cmp(&code[13], book.price, 6) < 0)
                goto forward;

            /* amount compare */
            int a_cmp = cmp(&code[20], book.amount, 6);

            if (a_cmp == 0) {
                /* FULL FILL */
                book.active = 0;
                goto drop;
            }

            if (a_cmp < 0) {
                /* incoming smaller */
                memcpy(book.amount, &code[20], 6);
                goto drop;
            }

            /* incoming larger */
            memcpy(&code[20], book.amount, 6);
            book.active = 0;

forward:
            rte_eth_tx_burst(port_id, 0, &m, 1);
            continue;

drop:
            rte_pktmbuf_free(m);
        }
    }
}
