<?php

// wait for some ms
$ms = (int) getenv("NGINX_SERVICE_DELAY_MS") ?: 0;
usleep($ms * 1000);
echo "Sleep " . $ms . " ms.<BR>";
echo "Hello World!<BR>\n";

?>
