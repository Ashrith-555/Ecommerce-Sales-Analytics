document.addEventListener("DOMContentLoaded", () => {

    console.log("Upload Module Ready");


    const uploadInput =
        document.querySelector("input[type='file']");

    const uploadButton =
        document.querySelector("button");


    uploadInput.addEventListener("change", () => {

        if (uploadInput.files.length > 0) {

            uploadButton.innerText =
                "Ready to Upload";

            uploadButton.style.background =
                "#16a34a";
        }

    });

});