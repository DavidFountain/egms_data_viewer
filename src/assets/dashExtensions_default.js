window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, layer, context) {
            layer.bindTooltip(`${feature.properties.pid} (${feature.properties.mean_velocity})`)
        },
        function1: function(feature, latlng, context) {
            const {
                min,
                max,
                colorscale,
                circleOptions,
                colorProp
            } = context.hideout;
            const csc = chroma.scale(colorscale).domain([min, max]); // chroma lib to construct colorscale
            circleOptions.fillColor = csc(feature.properties[colorProp]); // set color based on color prop
            return L.circleMarker(latlng, circleOptions); // render a simple circle marker
        },
        function2: function(feature, latlng, index, context) {
            const {
                min,
                max,
                colorscale,
                circleOptions,
                colorProp
            } = context.hideout;
            const csc = chroma.scale(colorscale).domain([min, max]);
            // Set color based on mean value of leaves.
            const leaves = index.getLeaves(feature.properties.cluster_id);
            let valueSum = 0;
            for (let i = 0; i < leaves.length; ++i) {
                valueSum += leaves[i].properties[colorProp]
            }
            const valueMean = valueSum / leaves.length;
            // Modify icon background color.
            const scatterIcon = L.DivIcon.extend({
                createIcon: function(oldIcon) {
                    let icon = L.DivIcon.prototype.createIcon.call(this, oldIcon);
                    icon.style.backgroundColor = this.options.color;
                    return icon;
                }
            })
            // Render a circle with the number of leaves written in the center.
            const icon = new scatterIcon({
                html: '<div style="background-color:white;"><span>' + feature.properties.point_count_abbreviated + '</span></div>',
                className: "marker-cluster",
                iconSize: L.point(40, 40),
                color: csc(valueMean)
            });
            return L.marker(latlng, {
                icon: icon
            })
        }
    }
});