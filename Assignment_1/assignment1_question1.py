"""
Usage:
    python assignment1_question1.py

"""

import sys
import os
import vtk


def find_dataset(filename):
    # Resolve the directory where this script lives
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Check both the script directory and a Data/ subfolder
    candidates = [
        os.path.join(script_dir, filename),
        os.path.join(script_dir, "Data", filename),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def linear_interp(p1, p2, v1, v2, isovalue):
    # Avoid division by zero for degenerate edges
    if abs(v2 - v1) < 1e-10:
        return p1
    # Parametric interpolation factor t in [0, 1]
    t = (isovalue - v1) / (v2 - v1)
    return (
        p1[0] + t * (p2[0] - p1[0]),
        p1[1] + t * (p2[1] - p1[1]),
        p1[2] + t * (p2[2] - p1[2]),
    )


def extract_isocontour(input_file, isovalue):

    # Read the 2D VTKImageData (.vti) file
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(input_file)
    reader.Update()
    image_data = reader.GetOutput()

    # Extract grid dimensions and spatial metadata
    dims    = image_data.GetDimensions()
    nx, ny  = dims[0], dims[1]
    spacing = image_data.GetSpacing()
    origin  = image_data.GetOrigin()

    # Retrieve the scalar field; fall back to first available array if needed
    scalars = image_data.GetPointData().GetScalars()
    if scalars is None:
        pd = image_data.GetPointData()
        for k in range(pd.GetNumberOfArrays()):
            scalars = pd.GetArray(k)
            if scalars:
                break
    if scalars is None:
        sys.exit(1)

    scalar_range = scalars.GetRange()

    # Containers for the output polyline geometry
    points          = vtk.vtkPoints()
    lines           = vtk.vtkCellArray()
    segment_count   = 0
    ambiguous_count = 0

    # Iterate over every 2D cell (pixel square) in the grid
    for j in range(ny - 1):
        for i in range(nx - 1):

            # Flat point indices for the four corners (CCW from bottom-left)
            idx_v0 = j       * nx + i           # bottom-left
            idx_v1 = j       * nx + (i + 1)     # bottom-right
            idx_v2 = (j + 1) * nx + (i + 1)     # top-right
            idx_v3 = (j + 1) * nx + i           # top-left

            # Scalar values at each corner
            s0 = scalars.GetTuple1(idx_v0)
            s1 = scalars.GetTuple1(idx_v1)
            s2 = scalars.GetTuple1(idx_v2)
            s3 = scalars.GetTuple1(idx_v3)

            # World-space coordinates of the cell's corners
            x0, y0 = origin[0] + i       * spacing[0], origin[1] + j       * spacing[1]
            x1, y1 = origin[0] + (i + 1) * spacing[0], origin[1] + (j + 1) * spacing[1]
            z       = origin[2]

            p0 = (x0, y0, z)   # bottom-left
            p1 = (x1, y0, z)   # bottom-right
            p2 = (x1, y1, z)   # top-right
            p3 = (x0, y1, z)   # top-left

            # Define the four edges of the cell in CCW order
            edges = [
                (p0, p1, s0, s1),   # bottom
                (p1, p2, s1, s2),   # right
                (p2, p3, s2, s3),   # top
                (p3, p0, s3, s0),   # left
            ]

            # Find edges that the isocontour crosses and interpolate crossing points
            crossings = []
            for pa, pb, sa, sb in edges:
                if (sa < isovalue <= sb) or (sb < isovalue <= sa):
                    crossings.append(linear_interp(pa, pb, sa, sb, isovalue))

            if len(crossings) == 2:
                # Standard case: connect the two crossing points with a line segment
                pid0 = points.InsertNextPoint(crossings[0])
                pid1 = points.InsertNextPoint(crossings[1])
                line = vtk.vtkLine()
                line.GetPointIds().SetId(0, pid0)
                line.GetPointIds().SetId(1, pid1)
                lines.InsertNextCell(line)
                segment_count += 1
            elif len(crossings) == 4:
                # Ambiguous saddle-point case
                ambiguous_count += 1

    # Assemble the extracted contour segments into a vtkPolyData object
    poly_data = vtk.vtkPolyData()
    poly_data.SetPoints(points)
    poly_data.SetLines(lines)

    # Write the result to a .vtp file alongside the script
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               f"isocontour_{isovalue}.vtp")
    writer = vtk.vtkXMLPolyDataWriter()
    writer.SetFileName(output_file)
    writer.SetInputData(poly_data)
    writer.Write()

    return poly_data


def display_isocontour(poly_data, isovalue):
    """Show extracted isocontour in a VTK popup window."""
    # Map the polydata geometry to graphics primitives
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(poly_data)

    # Style the contour lines (red, 2 px wide)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(1.0, 0.2, 0.2)
    actor.GetProperty().SetLineWidth(2.0)

    # On-screen HUD showing the current isovalue
    text = vtk.vtkTextActor()
    text.SetInput(f"Isovalue: {isovalue}")
    text.GetTextProperty().SetFontSize(22)
    text.GetTextProperty().SetColor(1.0, 1.0, 0.0)
    text.SetPosition(10, 10)

    # Set up renderer with dark background
    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)
    renderer.AddViewProp(text)   # AddViewProp is the non-deprecated replacement for AddActor2D
    renderer.SetBackground(0.08, 0.08, 0.08)
    renderer.ResetCamera()

    # Create an 800x800 render window
    window = vtk.vtkRenderWindow()
    window.AddRenderer(renderer)
    window.SetSize(800, 800)
    window.SetWindowName(f"2D Isocontour  |  isovalue = {isovalue}")

    # Launch the interactive window
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(window)
    window.Render()
    interactor.Start()


if __name__ == "__main__":
    # Locate the dataset file in the expected paths
    dataset_file = find_dataset("Isabel_2D.vti")

    # Ask for isovalue
    print("\nValid isovalue range for this dataset: (-1438, 630)")

    # Prompt the user for a valid numeric isovalue
    while True:
        try:
            isovalue = float(input("Enter isovalue: ").strip())
            break
        except ValueError:
            pass

    # Extract the isocontour and open the display window
    poly_data = extract_isocontour(dataset_file, isovalue)
    display_isocontour(poly_data, isovalue)