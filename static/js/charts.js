document.addEventListener("DOMContentLoaded", () => {

    console.log("Charts Initialized");


    const chartCards =
        document.querySelectorAll(".chart-card");

    chartCards.forEach((card) => {

        card.addEventListener("mouseenter", () => {

            card.style.transform =
                "scale(1.02)";

            card.style.transition =
                "0.3s";

        });


        card.addEventListener("mouseleave", () => {

            card.style.transform =
                "scale(1)";

        });

    });

});